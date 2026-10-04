"""Analytics stream — seeded random data generator.

Yields ``AnalyticsPoint`` values from a seeded RNG so results
are reproducible for a given seed.  The ``interval_ms`` controls
the delay between points, used for streaming demos.
"""

from __future__ import annotations

import random
import time
from collections.abc import Generator

from rpclab.service.errors import InvalidArgument
from rpclab.service.models import AnalyticsPoint

_VALID_METRICS = {"cpu", "latency", "sales"}

_METRIC_RANGES: dict[str, tuple[float, float]] = {
    "cpu": (0.0, 100.0),
    "latency": (1.0, 500.0),
    "sales": (10.0, 10_000.0),
}


def stream_analytics(
    metric: str,
    count: int,
    interval_ms: int = 0,
    seed: int = 42,
) -> Generator[AnalyticsPoint, None, None]:
    """Yield *count* analytics points for *metric*.

    Raises ``InvalidArgument`` for bad inputs.
    """
    if metric not in _VALID_METRICS:
        raise InvalidArgument(
            f"metric must be one of {sorted(_VALID_METRICS)}, got {metric!r}"
        )
    if type(count) is not int:
        raise InvalidArgument(f"count must be int, got {type(count).__name__}")
    if not (1 <= count <= 100):
        raise InvalidArgument(f"count must be 1..100, got {count}")
    if type(interval_ms) is not int:
        raise InvalidArgument(f"interval_ms must be int, got {type(interval_ms).__name__}")
    if not (0 <= interval_ms <= 2000):
        raise InvalidArgument(f"interval_ms must be 0..2000, got {interval_ms}")

    rng = random.Random(seed)
    lo, hi = _METRIC_RANGES[metric]
    running_sum = 0.0

    for seq in range(1, count + 1):
        value = rng.uniform(lo, hi)
        running_sum += value
        running_avg = running_sum / seq

        yield AnalyticsPoint(
            seq=seq,
            metric=metric,
            value=round(value, 4),
            running_avg=round(running_avg, 4),
            server_ts_ns=time.time_ns(),
        )

        if interval_ms > 0 and seq < count:
            time.sleep(interval_ms / 1000.0)
