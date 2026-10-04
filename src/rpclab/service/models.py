"""Domain models — pure data, no protocol awareness.

These are shared by all three transports. Money is always ``price_cents``
(int) to avoid float drift.  Factorial result is a decimal string because
protobuf has no bigint and Python 3.11+ limits int→str to 4300 digits.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Product:
    """A product in the inventory."""

    product_id: str
    name: str
    description: str
    price_cents: int  # always int — no floats for money
    currency: str
    stock_quantity: int
    tags: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    warehouse: str = ""

    def with_stock(self, new_quantity: int) -> Product:
        """Return a copy with an updated stock quantity."""
        return Product(
            product_id=self.product_id,
            name=self.name,
            description=self.description,
            price_cents=self.price_cents,
            currency=self.currency,
            stock_quantity=new_quantity,
            tags=self.tags,
            attributes=self.attributes,
            warehouse=self.warehouse,
        )


@dataclass(frozen=True, slots=True)
class StockResult:
    """Result of an ``update_stock`` call."""

    product_id: str
    new_quantity: int
    applied: bool


@dataclass(frozen=True, slots=True)
class PingResult:
    pong: bool
    server_time_ns: int


@dataclass(frozen=True, slots=True)
class FactorialResult:
    result: str  # decimal string
    digits: int


@dataclass(frozen=True, slots=True)
class AnalyticsPoint:
    seq: int
    metric: str
    value: float
    running_avg: float
    server_ts_ns: int
