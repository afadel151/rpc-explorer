"""Thread-safe in-memory inventory with idempotency cache.

Design decisions from the spec:
- In-memory dict, at least 20 deterministic seeded products.
- Guarded by ``threading.Lock`` for concurrent access.
- ``reset_inventory()`` restores the seed state.
- Idempotency: bounded OrderedDict (max 10k entries, oldest evicted).
  A repeated key returns the stored result with ``applied=False``.
- ``bool`` is rejected where ``int`` is expected (``type(x) is int``).
"""

from __future__ import annotations

import random
import threading
import time
from collections import OrderedDict
from typing import TYPE_CHECKING

from rpclab import config
from rpclab.service.errors import InsufficientStock, InvalidArgument, ProductNotFound
from rpclab.service.models import PingResult, Product, StockResult

if TYPE_CHECKING:
    pass

# ── Seed data ─────────────────────────────────────────────────────────

_WAREHOUSES = ["US-East", "US-West", "EU-Central", "EU-West", "APAC"]
_CURRENCIES = ["USD", "EUR", "GBP"]
_TAG_POOL = [
    "electronics", "gadgets", "home", "office", "outdoor",
    "premium", "sale", "new", "limited", "eco-friendly",
]
_ATTR_KEYS = ["color", "size", "material", "brand", "weight"]
_ATTR_VALUES = {
    "color": ["red", "blue", "green", "black", "white", "silver"],
    "size": ["S", "M", "L", "XL"],
    "material": ["plastic", "metal", "wood", "glass", "carbon-fiber"],
    "brand": ["Acme", "Globex", "Initech", "Umbrella", "Wonka"],
    "weight": ["100g", "250g", "500g", "1kg", "2kg"],
}


def _generate_products(seed: int, count: int) -> dict[str, Product]:
    """Generate deterministic products with a seeded RNG."""
    rng = random.Random(seed)
    products: dict[str, Product] = {}
    for i in range(count):
        pid = f"P-{1001 + i:04d}"
        n_tags = rng.randint(1, 4)
        tags = rng.sample(_TAG_POOL, n_tags)
        n_attrs = rng.randint(1, 3)
        attr_keys = rng.sample(_ATTR_KEYS, n_attrs)
        attrs = {k: rng.choice(_ATTR_VALUES[k]) for k in attr_keys}
        products[pid] = Product(
            product_id=pid,
            name=f"Product {pid}",
            description=f"A fine product in the {rng.choice(_WAREHOUSES)} warehouse.",
            price_cents=rng.randint(100, 100_000),
            currency=rng.choice(_CURRENCIES),
            stock_quantity=rng.randint(5, 500),
            tags=tags,
            attributes=attrs,
            warehouse=rng.choice(_WAREHOUSES),
        )
    return products


# ── Service ───────────────────────────────────────────────────────────


class InventoryService:
    """Thread-safe inventory with idempotency cache."""

    def __init__(
        self,
        seed: int = config.INVENTORY_SEED,
        product_count: int = config.PRODUCT_COUNT,
        cache_size: int = config.IDEMPOTENCY_CACHE_SIZE,
    ) -> None:
        self._seed = seed
        self._product_count = product_count
        self._cache_size = cache_size
        self._lock = threading.Lock()
        self._products: dict[str, Product] = _generate_products(seed, product_count)
        self._idempotency_cache: OrderedDict[str, StockResult] = OrderedDict()

    # ── Ping ──────────────────────────────────────────────────────

    def ping(self, sleep_ms: int = 0) -> PingResult:
        """Return pong, optionally sleeping first (for timeout demos)."""
        if type(sleep_ms) is not int:
            raise InvalidArgument(f"sleep_ms must be int, got {type(sleep_ms).__name__}")
        if not (0 <= sleep_ms <= config.SLEEP_MAX_MS):
            raise InvalidArgument(f"sleep_ms must be 0..{config.SLEEP_MAX_MS}, got {sleep_ms}")
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000.0)
        return PingResult(pong=True, server_time_ns=time.time_ns())

    # ── Product details ───────────────────────────────────────────

    def get_product_details(self, product_id: str) -> Product:
        """Return a product by ID.  Raises ``ProductNotFound``."""
        with self._lock:
            product = self._products.get(product_id)
        if product is None:
            raise ProductNotFound(product_id)
        return product

    # ── Stock update ──────────────────────────────────────────────

    def update_stock(
        self,
        product_id: str,
        delta: int,
        idempotency_key: str | None = None,
    ) -> StockResult:
        """Adjust stock by *delta*.

        Raises ``ProductNotFound`` or ``InsufficientStock``.
        If *idempotency_key* was seen before, returns the cached result
        with ``applied=False``.
        """
        # Strict type check: reject bool masquerading as int
        if type(delta) is not int:
            raise InvalidArgument(f"delta must be int, got {type(delta).__name__}")
        if delta == 0:
            raise InvalidArgument("delta must be nonzero")
        if not (config.STOCK_DELTA_MIN <= delta <= config.STOCK_DELTA_MAX):
            raise InvalidArgument(
                f"delta must be {config.STOCK_DELTA_MIN}..{config.STOCK_DELTA_MAX}, got {delta}"
            )

        with self._lock:
            # Idempotency check
            if idempotency_key and idempotency_key in self._idempotency_cache:
                cached = self._idempotency_cache[idempotency_key]
                return StockResult(
                    product_id=cached.product_id,
                    new_quantity=cached.new_quantity,
                    applied=False,
                )

            product = self._products.get(product_id)
            if product is None:
                raise ProductNotFound(product_id)

            new_qty = product.stock_quantity + delta
            if new_qty < 0:
                raise InsufficientStock(product_id, product.stock_quantity, delta)

            self._products[product_id] = product.with_stock(new_qty)
            result = StockResult(product_id=product_id, new_quantity=new_qty, applied=True)

            # Cache the result
            if idempotency_key:
                self._idempotency_cache[idempotency_key] = result
                # Evict oldest if over capacity
                while len(self._idempotency_cache) > self._cache_size:
                    self._idempotency_cache.popitem(last=False)

            return result

    # ── Reset ─────────────────────────────────────────────────────

    def reset_inventory(self) -> bool:
        """Restore inventory to seed state, clear idempotency cache."""
        with self._lock:
            self._products = _generate_products(self._seed, self._product_count)
            self._idempotency_cache.clear()
        return True
