#!/usr/bin/env python3
r"""Search a repo for risky migration patterns.

Usage:
  python scripts/risky_patterns.py --profile sqlalchemy
  python scripts/risky_patterns.py --pattern 'session\.query' --pattern 'engine\.execute'
  python scripts/risky_patterns.py --profile sqlalchemy --json
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_IGNORES = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}

PROFILES = {
    "lifecycle": [r"\bsave\(", r"\bclose\(", r"\bcommit\(", r"\brollback\(", r"\bflush\(", r"\bconnect\(", r"\bexecute\("],
    "sqlalchemy": [r"engine\.execute", r"session\.query", r"\bautocommit\b", r"\bcommit\(", r"\brollback\(", r"\bclose\("],
    "pydantic": [r"BaseModel", r"BaseSettings", r"parse_obj", r"parse_raw", r"\.dict\(", r"\.json\(", r"@validator", r"@root_validator"],
    "pandas": [r"read_csv", r"to_datetime", r"astype", r"groupby", r"merge\(", r"\.append\("],
    "http": [r"requests\.", r"urllib3", r"httpx\.", r"timeout=", r"verify=", r"Retry\(", r"HTTPAdapter"],
}


@dataclass
class PatternHit:
    file: str
    line: int
    pattern: str
    content: str


@dataclass
class ScanResult:
    hits: list[PatternHit] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.hits)

    def to_json(self) -> str:
        return json.dumps({"hits": [asdict(h) for h in self.hits], "total": self.total}, indent=2)

    def to_text(self) -> str:
        lines = [f"{h.file}:{h.line}: [{h.pattern}] {h.content}" for h in self.hits]
        lines.append(f"\nTotal hits: {self.total}")
        return "\n".join(lines)


def iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in DEFAULT_IGNORES for part in path.parts):
            continue
        yield path


def scan_patterns(root: Path, patterns: list[str]) -> ScanResult:
    compiled = [(p, re.compile(p)) for p in patterns]
    result = ScanResult()

    for path in iter_py_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, start=1):
            for label, rx in compiled:
                if rx.search(line):
                    result.hits.append(PatternHit(file=str(path), line=lineno, pattern=label, content=line.strip()))

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--profile", action="append", choices=sorted(PROFILES))
    parser.add_argument("--pattern", action="append", default=[])
    parser.add_argument("--json", action="store_true", dest="output_json")
    args = parser.parse_args()

    patterns: list[str] = []
    for profile in args.profile or []:
        patterns.extend(PROFILES[profile])
    patterns.extend(args.pattern)

    if not patterns:
        parser.error("Provide --profile or --pattern")

    result = scan_patterns(Path(args.root), patterns)

    if args.output_json:
        print(result.to_json())
    else:
        print(result.to_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())