"""Development helper script: proto, test, lint, demo.

Usage:
    uv run python scripts/dev.py proto   — generate protobuf code
    uv run python scripts/dev.py test    — run pytest
    uv run python scripts/dev.py lint    — run ruff
    uv run python scripts/dev.py demo    — placeholder for full demo runner
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO_DIR = ROOT / "proto"
GENERATED_BASE = ROOT / "src" / "rpclab" / "grpc_rpc" / "generated"

PROTO_VERSIONS = {
    "v1": PROTO_DIR / "v1",
    "v2_compat": PROTO_DIR / "v2_compatible",
    "v2_breaking": PROTO_DIR / "v2_breaking",
}


def _fix_imports(generated_dir: Path) -> None:
    """Rewrite bare ``import inventory_pb2`` to a relative import.

    grpc_tools.protoc emits ``import inventory_pb2 as ...`` inside
    ``*_pb2_grpc.py``.  When the generated files live inside a package
    this breaks.  We mechanically rewrite it to
    ``from . import inventory_pb2 as ...``.
    """
    for grpc_file in generated_dir.glob("*_pb2_grpc.py"):
        text = grpc_file.read_text()
        fixed = re.sub(
            r"^(import inventory_pb2 as )",
            r"from . \1",
            text,
            flags=re.MULTILINE,
        )
        if fixed != text:
            grpc_file.write_text(fixed)
            print(f"  ↳ fixed import in {grpc_file.name}")


def cmd_proto() -> None:
    """Generate protobuf Python code for all contract versions."""
    from grpc_tools import protoc  # type: ignore[import-untyped]

    for version_name, proto_path in PROTO_VERSIONS.items():
        out_dir = GENERATED_BASE / version_name
        out_dir.mkdir(parents=True, exist_ok=True)

        # Write __init__.py so the directory is a package
        init_file = out_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Generated protobuf code — DO NOT EDIT."""\n')

        proto_file = proto_path / "inventory.proto"
        if not proto_file.exists():
            print(f"✗ {proto_file} not found, skipping {version_name}")
            continue

        args = [
            "grpc_tools.protoc",
            f"--proto_path={proto_path}",
            f"--python_out={out_dir}",
            f"--grpc_python_out={out_dir}",
            str(proto_file),
        ]
        print(f"· Generating {version_name} → {out_dir.relative_to(ROOT)}")
        exit_code = protoc.main(args)
        if exit_code != 0:
            print(f"  ✗ protoc failed for {version_name} (exit {exit_code})")
            sys.exit(1)

        _fix_imports(out_dir)

    print("✓ All proto versions generated.")


def cmd_test() -> None:
    """Run pytest."""
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=ROOT))


def cmd_lint() -> None:
    """Run ruff check + format check."""
    ret = subprocess.call([sys.executable, "-m", "ruff", "check", "src/", "tests/"], cwd=ROOT)
    ret2 = subprocess.call(
        [sys.executable, "-m", "ruff", "format", "--check", "src/", "tests/"], cwd=ROOT
    )
    sys.exit(max(ret, ret2))


def cmd_demo() -> None:
    """Placeholder — full demo runner comes in Phase 11."""
    print("Demo command not implemented yet. Run `python -m rpclab` for the CLI.")


COMMANDS = {
    "proto": cmd_proto,
    "test": cmd_test,
    "lint": cmd_lint,
    "demo": cmd_demo,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: {sys.executable} scripts/dev.py <{'|'.join(COMMANDS)}>")
        sys.exit(1)
    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
