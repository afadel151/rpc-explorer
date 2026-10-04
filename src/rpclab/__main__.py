"""Entry point: ``python -m rpclab``."""

from __future__ import annotations

import sys


def main() -> None:
    """Minimal entry point — full Typer CLI comes in Phase 11."""
    if len(sys.argv) > 1 and sys.argv[1] == "doctor":
        from rpclab.doctor import run_doctor

        ok = run_doctor()
        sys.exit(0 if ok else 1)

    # Default: show help
    print("RPC Explorer & Benchmark Lab")
    print()
    print("Available commands:")
    print("  doctor    — run pre-flight checks")
    print()
    print("Usage: python -m rpclab doctor")


if __name__ == "__main__":
    main()
