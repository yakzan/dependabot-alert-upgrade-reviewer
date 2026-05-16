#!/usr/bin/env python3
r"""Search a repo for risky migration patterns.

Usage:
  python scripts/risky_patterns.py --profile sqlalchemy
  python scripts/risky_patterns.py --pattern 'session\.query' --pattern 'engine\.execute'
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

DEFAULT_IGNORES = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}

PROFILES = {
    "lifecycle": [r"\bsave\(", r"\bclose\(", r"\bcommit\(", r"\brollback\(", r"\bflush\(", r"\bconnect\(", r"\bexecute\("],
    "sqlalchemy": [r"engine\.execute", r"session\.query", r"\bautocommit\b", r"\bcommit\(", r"\brollback\(", r"\bclose\("],
    "pydantic": [r"BaseModel", r"BaseSettings", r"parse_obj", r"parse_raw", r"\.dict\(", r"\.json\(", r"@validator", r"@root_validator"],
    "pandas": [r"read_csv", r"to_datetime", r"astype", r"groupby", r"merge\(", r"\.append\("],
    "http": [r"requests\.", r"urllib3", r"httpx\.", r"timeout=", r"verify=", r"Retry\(", r"HTTPAdapter"],
}


def iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in DEFAULT_IGNORES for part in path.parts):
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--profile", action="append", choices=sorted(PROFILES))
    parser.add_argument("--pattern", action="append", default=[])
    args = parser.parse_args()

    patterns: list[str] = []
    for profile in args.profile or []:
        patterns.extend(PROFILES[profile])
    patterns.extend(args.pattern)

    if not patterns:
        parser.error("Provide --profile or --pattern")

    compiled = [(p, re.compile(p)) for p in patterns]
    root = Path(args.root)
    hits = 0

    for path in iter_py_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, start=1):
            for label, rx in compiled:
                if rx.search(line):
                    print(f"{path}:{lineno}: [{label}] {line.strip()}")
                    hits += 1

    print(f"\nTotal hits: {hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
