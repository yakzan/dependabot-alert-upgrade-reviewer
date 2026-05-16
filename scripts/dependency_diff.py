#!/usr/bin/env python3
"""Print dependency-related files changed between two git refs.

This is intentionally conservative. It does not try to solve all lockfile formats;
it gives the agent a deterministic starting point for inspection.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

DEP_FILES = (
    "requirements",
    "pyproject.toml",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    ".python-version",
)


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)


def is_dep_file(path: str) -> bool:
    name = Path(path).name
    return any(name.startswith(prefix) or name == prefix for prefix in DEP_FILES)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="main")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    diff_name = run(["git", "diff", "--name-only", f"{args.base}...{args.head}"])
    files = [line.strip() for line in diff_name.splitlines() if line.strip()]
    dep_files = [f for f in files if is_dep_file(f)]

    if not dep_files:
        print("No dependency/runtime files changed.")
        return 0

    print("Dependency/runtime files changed:")
    for f in dep_files:
        print(f"- {f}")

    print("\nRelevant diff:")
    for f in dep_files:
        print(f"\n--- {f} ---")
        try:
            print(run(["git", "diff", f"{args.base}...{args.head}", "--", f]))
        except subprocess.CalledProcessError as exc:
            print(exc.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
