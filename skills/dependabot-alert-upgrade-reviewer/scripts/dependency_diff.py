#!/usr/bin/env python3
"""Print dependency-related files changed between two git refs.

This is intentionally conservative. It does not try to solve all lockfile formats;
it gives the agent a deterministic starting point for inspection.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

DEP_FILES = (
    "requirements",
    "constraints",
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
    return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)


def detect_default_branch() -> str:
    """Detect the default branch name from git refs.

    Checks, in order:
    1. ``origin/HEAD`` symbolic ref (works after ``git fetch``)
    2. Local refs for ``main`` and ``master``
    3. Falls back to ``main``
    """
    try:
        out = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
        return out.strip().replace("refs/remotes/origin/", "")
    except subprocess.CalledProcessError:
        pass
    for candidate in ("main", "master"):
        try:
            run(["git", "rev-parse", "--verify", candidate])
            return candidate
        except subprocess.CalledProcessError:
            continue
    return "main"


def is_dep_file(path: str) -> bool:
    parts = Path(path).parts
    name = Path(path).name
    if any(name.startswith(prefix) or name == prefix for prefix in DEP_FILES):
        return True
    # Directory-style layouts: requirements/dev.txt, constraints/prod.in, etc.
    if name.endswith((".txt", ".in")) and any(p in ("requirements", "constraints") for p in parts[:-1]):
        return True
    return False


def get_dep_diff(base: str, head: str, path: str) -> str:
    try:
        return run(["git", "diff", f"{base}...{head}", "--", path])
    except subprocess.CalledProcessError as exc:
        return exc.output


@dataclass
class DepDiffResult:
    base: str
    head: str
    dep_files: list[str] = field(default_factory=list)
    diffs: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "base": self.base,
                "head": self.head,
                "dep_files": self.dep_files,
                "diffs": self.diffs,
            },
            indent=2,
        )

    def to_text(self) -> str:
        if not self.dep_files:
            return "No dependency/runtime files changed."

        lines = ["Dependency/runtime files changed:"]
        for f in self.dep_files:
            lines.append(f"- {f}")

        lines.append("\nRelevant diff:")
        for f in self.dep_files:
            lines.append(f"\n--- {f} ---")
            lines.append(self.diffs.get(f, ""))

        return "\n".join(lines)


def scan_dep_files(base: str, head: str) -> DepDiffResult:
    diff_name = run(["git", "diff", "--name-only", f"{base}...{head}"])
    files = [line.strip() for line in diff_name.splitlines() if line.strip()]
    dep_files = [f for f in files if is_dep_file(f)]

    result = DepDiffResult(base=base, head=head, dep_files=dep_files)

    for f in dep_files:
        result.diffs[f] = get_dep_diff(base, head, f)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--json", action="store_true", dest="output_json")
    args = parser.parse_args()

    base = args.base or detect_default_branch()

    result = scan_dep_files(base, args.head)

    if args.output_json:
        print(result.to_json())
    else:
        print(result.to_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())