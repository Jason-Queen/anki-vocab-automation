#!/usr/bin/env python3
"""Legacy bootstrap shim for the uv-based workflow."""

import sys


def main():
    """Explain the supported installation flow and exit."""
    print("Legacy scripts/setup.py bootstrap is no longer supported.")
    print("Use the uv workflow instead:")
    print(
        "  1. Install uv: "
        "https://docs.astral.sh/uv/getting-started/installation/"
    )
    print("  2. Install runtime dependencies: uv sync")
    print(
        "  3. Install maintainer tools when needed: "
        "uv sync --extra dev --extra test"
    )
    print("  4. Run the app: uv run python app.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
