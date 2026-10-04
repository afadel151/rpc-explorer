"""Domain exceptions — protocol-ignorant.

Each transport layer maps these to its own error representation
(custom RPC wire codes, gRPC status codes, HTTP status codes).
The service layer never knows about status codes.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base for all domain errors."""


class ProductNotFound(ServiceError):
    """Raised when a product_id does not exist in the inventory."""

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")


class InsufficientStock(ServiceError):
    """Raised when a stock update would drive quantity below zero."""

    def __init__(self, product_id: str, current: int, requested_delta: int) -> None:
        self.product_id = product_id
        self.current = current
        self.requested_delta = requested_delta
        super().__init__(
            f"Insufficient stock for {product_id}: "
            f"current={current}, delta={requested_delta}"
        )


class InvalidArgument(ServiceError):
    """Raised for bad input values (out of range, wrong type)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
