"""Pre-flight checks: Python version, dependencies, generated code, free ports.

Run via ``python -m rpclab doctor``.
"""

from __future__ import annotations

import importlib
import socket
import sys

from rich.console import Console
from rich.table import Table

from rpclab import config

console = Console()

# ── Individual checks ─────────────────────────────────────────────────


def _check_python_version() -> tuple[bool, str]:
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 12
    detail = f"{v.major}.{v.minor}.{v.micro}"
    return ok, f"Python {detail}" + ("" if ok else " (need ≥3.12)")


def _check_import(package: str) -> tuple[bool, str]:
    try:
        mod = importlib.import_module(package)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        return True, f"{package} {version}"
    except ImportError:
        return False, f"{package} — NOT FOUND"


def _check_generated_code() -> tuple[bool, str]:
    try:
        from rpclab.grpc_rpc.generated.v1 import inventory_pb2  # noqa: F401

        return True, "v1 generated code present"
    except ImportError:
        return False, "v1 generated code MISSING — run: uv run python scripts/dev.py proto"


def _check_port_free(port: int, name: str) -> tuple[bool, str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            s.bind((config.HOST, port))
        return True, f":{port} ({name}) — free"
    except OSError:
        return False, f":{port} ({name}) — IN USE"


# ── Runner ────────────────────────────────────────────────────────────

_CHECKS: list[tuple[str, ...]] = [
    ("Python version",),
    ("grpcio",),
    ("protobuf",),
    ("fastapi",),
    ("uvicorn",),
    ("httpx",),
    ("typer",),
    ("rich",),
    ("Generated proto code",),
]

_PORT_CHECKS = [
    (config.CUSTOM_RPC_PORT, "custom RPC"),
    (config.GRPC_PORT, "gRPC"),
    (config.REST_PORT, "REST"),
    (config.PROXY_CONTROL_PORT, "proxy control"),
]


def run_doctor() -> bool:
    """Run all doctor checks.  Returns True if everything passed."""
    table = Table(title="rpclab doctor", show_lines=False)
    table.add_column("Status", width=4, justify="center")
    table.add_column("Check")
    table.add_column("Detail")

    all_ok = True

    # Python version
    ok, detail = _check_python_version()
    all_ok &= ok
    table.add_row("✓" if ok else "✗", "Python version", detail)

    # Package imports
    import_map = {"grpcio": "grpc", "protobuf": "google.protobuf"}
    for pkg in ("grpcio", "protobuf", "fastapi", "uvicorn", "httpx", "typer", "rich"):
        pkg_import = import_map.get(pkg, pkg)
        ok, detail = _check_import(pkg_import)
        all_ok &= ok
        table.add_row("✓" if ok else "✗", f"import {pkg}", detail)

    # Generated code
    ok, detail = _check_generated_code()
    all_ok &= ok
    table.add_row("✓" if ok else "✗", "Generated proto code", detail)

    # Port checks
    for port, name in _PORT_CHECKS:
        ok, detail = _check_port_free(port, name)
        all_ok &= ok
        table.add_row("✓" if ok else "✗", f"Port {port}", detail)

    console.print()
    console.print(table)
    console.print()

    if all_ok:
        console.print("[bold green]All checks passed.[/bold green]")
    else:
        console.print("[bold red]Some checks failed — see above.[/bold red]")

    return all_ok
