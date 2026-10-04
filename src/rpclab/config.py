"""Central configuration: ports, limits, timeouts.

Every magic number in the project lives here. Import from ``rpclab.config``
— never hard-code port numbers or buffer sizes in other modules.
"""

from __future__ import annotations

# ── Server ports (direct) ─────────────────────────────────────────────
CUSTOM_RPC_PORT = 9000
GRPC_PORT = 50051
REST_PORT = 8080

# ── Proxy listener ports ──────────────────────────────────────────────
PROXY_CUSTOM_PORT = 19000
PROXY_GRPC_PORT = 15051
PROXY_REST_PORT = 18080
PROXY_CONTROL_PORT = 19999

# ── Host ──────────────────────────────────────────────────────────────
HOST = "127.0.0.1"

# ── Custom RPC limits ─────────────────────────────────────────────────
MAX_FRAME_BYTES = 1 * 1024 * 1024  # 1 MiB
LENGTH_PREFIX_BYTES = 4  # big-endian unsigned

# ── Domain limits ─────────────────────────────────────────────────────
FACTORIAL_MAX_N = 1000
SLEEP_MAX_MS = 5000
STOCK_DELTA_MIN = -10_000
STOCK_DELTA_MAX = 10_000
IDEMPOTENCY_CACHE_SIZE = 10_000
PRODUCT_COUNT = 20
INVENTORY_SEED = 42

# ── Timeouts (seconds) ────────────────────────────────────────────────
DEFAULT_CALL_TIMEOUT = 5.0
CONNECT_TIMEOUT = 3.0
REST_HEALTH_CHECK_TIMEOUT = 15.0

# ── Benchmarks ────────────────────────────────────────────────────────
BENCHMARK_WARMUP = 100
BENCHMARK_DEFAULT_N = 1000
BENCHMARK_DELAY_N = 30

# ── Thread pool ───────────────────────────────────────────────────────
SERVER_WORKER_THREADS = 8
