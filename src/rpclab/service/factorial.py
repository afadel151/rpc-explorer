"""Factorial service — result is always a decimal string.

Protobuf has no bigint and int64 overflows at 21!.
Python 3.11+ limits int→str conversion to 4300 digits by default;
1000! has 2568 digits, so the cap of 1000 is safe.
"""

from __future__ import annotations

import math

from rpclab import config
from rpclab.service.errors import InvalidArgument
from rpclab.service.models import FactorialResult


def calculate_factorial(n: int) -> FactorialResult:
    """Compute n! and return the result as a decimal string.

    Raises ``InvalidArgument`` if *n* is out of range or not an int.
    """
    if type(n) is not int:
        raise InvalidArgument(f"n must be int, got {type(n).__name__}")
    if not (0 <= n <= config.FACTORIAL_MAX_N):
        raise InvalidArgument(f"n must be 0..{config.FACTORIAL_MAX_N}, got {n}")

    result_str = str(math.factorial(n))
    return FactorialResult(result=result_str, digits=len(result_str))
