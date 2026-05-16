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
    "lifecycle": [
        r"\bsave\(", r"\bclose\(", r"\bcommit\(", r"\brollback\(",
        r"\bflush\(", r"\bconnect\(", r"\bdisconnect\(", r"\bexecute\(",
        r"\bdispose\(", r"\bopen\(", r"\bread\(", r"\bwrite\(",
    ],
    "sqlalchemy": [
        r"engine\.execute", r"session\.execute", r"session\.query",
        r"\.scalars\(", r"\.scalar\(", r"\.fetchone\(", r"\.fetchall\(",
        r"\.mappings\(", r"\bResult\b",
        r"\bautocommit\b", r"\bcommit\(", r"\brollback\(", r"\bclose\(", r"\bflush\(",
        r"\bcreate_engine\b", r"\bsessionmaker\b", r"\bscoped_session\b",
        r"\bdeclarative_base\b", r"\bMapped\b", r"\bmapped_column\b",
        r"\bselect\(", r"\btext\(", r"\bMetaData\b",
        r"\bget_bind\b", r"\bdispose\b", r"\bback_populates\b",
    ],
    "pydantic": [
        r"BaseModel", r"BaseSettings", r"ConfigDict",
        r"parse_obj\b", r"parse_raw\b", r"parse_file\b", r"from_orm\b",
        r"\.dict\(", r"\.json\(", r"model_dump\b", r"model_dump_json\b",
        r"model_validate\b", r"model_validate_json\b",
        r"@validator\b", r"@root_validator\b", r"@field_validator\b", r"@model_validator\b",
        r"field_validator\(", r"model_validator\(",
        r"orm_mode", r"from_attributes",
        r"allow_population_by_field_name", r"populate_by_name",
        r"Field\(", r"Annotated\[",
        r"computed_field", r"field_serializer",
    ],
    "pandas": [
        r"read_csv", r"read_excel", r"to_datetime", r"to_numeric",
        r"\.astype\b", r"\.fillna\b", r"\.dropna\b", r"\.drop_duplicates\b",
        r"\.groupby\b", r"\.agg\b", r"\.merge\b", r"\.join\b", r"\.concat\b",
        r"\.append\b", r"\.ix\[", r"\.iteritems\b",
        r"\.sort_values\b", r"\.pivot_table\b", r"\.resample\b", r"\.rolling\b",
        r"inplace=True", r"copy=True", r"infer_objects",
    ],
    "http": [
        r"requests\.", r"urllib3", r"httpx\.",
        r"\.get\b", r"\.post\b", r"\.put\b", r"\.delete\b", r"\.request\(",
        r"timeout=", r"verify=", r"cert=", r"proxies=",
        r"Retry\(", r"HTTPAdapter", r"mount\(",
        r"Session\(", r"raise_for_status",
        r"ConnectionError", r"Timeout\b", r"SSLError", r"HTTPError",
        r"stream=", r"allow_redirects", r"\bclose\(",
    ],
    "pytest": [
        r"pytest_plugins", r"@pytest\.fixture", r"yield",
        r"pytest\.mark", r"xfail", r"skipif",
        r"pytest\.raises", r"warns\(", r"deprecated_call",
        r"filterwarnings", r"addopts",
        r"pytest\.ini", r"conftest\.py",
    ],
    "python-runtime": [
        r"from collections import",
        r"asyncio\.coroutine", r"get_event_loop", r"loop=",
        r"import imp\b", r"from imp import", r"distutils",
        r"typing_extensions", r"dataclasses", r"importlib_metadata",
        r"pathlib2", r"configparser",
        r"python_requires", r"requires-python",
        r"Programming Language :: Python :: 3\.[0-9]",
    ],
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