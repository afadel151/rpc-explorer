"""Tests for the service layer — Phase 1 acceptance criteria.

Covers:
- Factorial: 0 and 1000 (boundary), type rejection
- Inventory: not found, insufficient stock, concurrent updates,
  idempotency dedup, bool rejection, reset
- Analytics: correct count, running average, metric validation
"""

from __future__ import annotations

import threading

import pytest

from rpclab.service.analytics import stream_analytics
from rpclab.service.errors import InsufficientStock, InvalidArgument, ProductNotFound
from rpclab.service.factorial import calculate_factorial
from rpclab.service.inventory import InventoryService


# ── Factorial ─────────────────────────────────────────────────────────


class TestFactorial:
    def test_factorial_zero(self) -> None:
        result = calculate_factorial(0)
        assert result.result == "1"
        assert result.digits == 1

    def test_factorial_1000(self) -> None:
        result = calculate_factorial(1000)
        assert result.digits == 2568  # 1000! has exactly 2568 digits
        assert result.result.startswith("4023872600")
        assert result.result.endswith("0000000000")

    def test_factorial_negative_rejected(self) -> None:
        with pytest.raises(InvalidArgument, match="0..1000"):
            calculate_factorial(-1)

    def test_factorial_over_max_rejected(self) -> None:
        with pytest.raises(InvalidArgument, match="0..1000"):
            calculate_factorial(1001)

    def test_factorial_bool_rejected(self) -> None:
        """isinstance(True, int) is True in Python, but type(True) is not int."""
        with pytest.raises(InvalidArgument, match="bool"):
            calculate_factorial(True)  # type: ignore[arg-type]


# ── Inventory ─────────────────────────────────────────────────────────


class TestInventory:
    @pytest.fixture()
    def svc(self) -> InventoryService:
        return InventoryService(seed=42, product_count=20)

    def test_get_product_exists(self, svc: InventoryService) -> None:
        product = svc.get_product_details("P-1001")
        assert product.product_id == "P-1001"
        assert product.price_cents > 0
        assert product.currency in ("USD", "EUR", "GBP")

    def test_product_not_found(self, svc: InventoryService) -> None:
        with pytest.raises(ProductNotFound):
            svc.get_product_details("P-9999")

    def test_update_stock_positive(self, svc: InventoryService) -> None:
        original = svc.get_product_details("P-1001")
        result = svc.update_stock("P-1001", 10)
        assert result.applied is True
        assert result.new_quantity == original.stock_quantity + 10

    def test_update_stock_negative(self, svc: InventoryService) -> None:
        original = svc.get_product_details("P-1001")
        result = svc.update_stock("P-1001", -1)
        assert result.applied is True
        assert result.new_quantity == original.stock_quantity - 1

    def test_insufficient_stock(self, svc: InventoryService) -> None:
        product = svc.get_product_details("P-1001")
        with pytest.raises(InsufficientStock):
            svc.update_stock("P-1001", -(product.stock_quantity + 1))

    def test_update_stock_not_found(self, svc: InventoryService) -> None:
        with pytest.raises(ProductNotFound):
            svc.update_stock("P-9999", 1)

    def test_update_stock_zero_rejected(self, svc: InventoryService) -> None:
        with pytest.raises(InvalidArgument, match="nonzero"):
            svc.update_stock("P-1001", 0)

    def test_bool_rejected_for_delta(self, svc: InventoryService) -> None:
        """True is a bool, not an int for our purposes."""
        with pytest.raises(InvalidArgument, match="bool"):
            svc.update_stock("P-1001", True)  # type: ignore[arg-type]

    def test_idempotency_dedup(self, svc: InventoryService) -> None:
        original = svc.get_product_details("P-1001")
        key = "test-key-001"

        # First call: applied
        r1 = svc.update_stock("P-1001", -1, idempotency_key=key)
        assert r1.applied is True
        assert r1.new_quantity == original.stock_quantity - 1

        # Second call with same key: NOT applied, stock unchanged
        r2 = svc.update_stock("P-1001", -1, idempotency_key=key)
        assert r2.applied is False
        assert r2.new_quantity == r1.new_quantity

        # Verify actual stock didn't change
        updated = svc.get_product_details("P-1001")
        assert updated.stock_quantity == r1.new_quantity

    def test_concurrent_update_stock_never_negative(self, svc: InventoryService) -> None:
        """10 threads each decrement by 1 concurrently. Stock must never go below 0."""
        product = svc.get_product_details("P-1001")
        initial_qty = product.stock_quantity
        n_threads = 10
        results: list[StockResult | Exception] = [None] * n_threads  # type: ignore[list-item]

        # Import here to demonstrate the type (already imported above in real code)
        from rpclab.service.models import StockResult

        def _decrement(idx: int) -> None:
            try:
                results[idx] = svc.update_stock("P-1001", -1)
            except Exception as exc:
                results[idx] = exc

        threads = [threading.Thread(target=_decrement, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Count successful decrements
        successes = sum(1 for r in results if isinstance(r, StockResult) and r.applied)
        failures = sum(1 for r in results if isinstance(r, InsufficientStock))
        assert successes + failures == n_threads

        # Final stock = initial - successes, and must be >= 0
        final = svc.get_product_details("P-1001")
        assert final.stock_quantity == initial_qty - successes
        assert final.stock_quantity >= 0

    def test_reset_inventory(self, svc: InventoryService) -> None:
        original = svc.get_product_details("P-1001")
        svc.update_stock("P-1001", -1)
        svc.reset_inventory()
        restored = svc.get_product_details("P-1001")
        assert restored.stock_quantity == original.stock_quantity


# ── Analytics ─────────────────────────────────────────────────────────


class TestAnalytics:
    def test_stream_correct_count(self) -> None:
        points = list(stream_analytics("cpu", 10, interval_ms=0))
        assert len(points) == 10

    def test_stream_running_average(self) -> None:
        points = list(stream_analytics("sales", 5, interval_ms=0, seed=99))
        # Running avg of first point should equal the first value
        assert points[0].running_avg == points[0].value
        # Running avg of all points should be mean of all values
        total = sum(p.value for p in points)
        expected_avg = round(total / len(points), 4)
        assert abs(points[-1].running_avg - expected_avg) < 0.01

    def test_stream_sequence_numbers(self) -> None:
        points = list(stream_analytics("latency", 5, interval_ms=0))
        seqs = [p.seq for p in points]
        assert seqs == [1, 2, 3, 4, 5]

    def test_invalid_metric(self) -> None:
        with pytest.raises(InvalidArgument, match="metric"):
            list(stream_analytics("memory", 5))

    def test_count_out_of_range(self) -> None:
        with pytest.raises(InvalidArgument, match="count"):
            list(stream_analytics("cpu", 0))

    def test_reproducible_with_seed(self) -> None:
        a = list(stream_analytics("cpu", 10, interval_ms=0, seed=42))
        b = list(stream_analytics("cpu", 10, interval_ms=0, seed=42))
        assert [p.value for p in a] == [p.value for p in b]


# ── Ping ──────────────────────────────────────────────────────────────


class TestPing:
    @pytest.fixture()
    def svc(self) -> InventoryService:
        return InventoryService()

    def test_ping_basic(self, svc: InventoryService) -> None:
        result = svc.ping(0)
        assert result.pong is True
        assert result.server_time_ns > 0

    def test_ping_bool_rejected(self, svc: InventoryService) -> None:
        with pytest.raises(InvalidArgument, match="bool"):
            svc.ping(True)  # type: ignore[arg-type]

    def test_ping_out_of_range(self, svc: InventoryService) -> None:
        with pytest.raises(InvalidArgument, match="sleep_ms"):
            svc.ping(-1)
