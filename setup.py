#!/usr/bin/env python3
"""Setuptools compatibility shim plus a legacy bootstrap warning."""

import sys


if __name__ == "__main__" and len(sys.argv) == 1:
    print("Legacy setup.py bootstrap is no longer supported.")
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
    raise SystemExit(1)


from setuptools import setup


setup()
