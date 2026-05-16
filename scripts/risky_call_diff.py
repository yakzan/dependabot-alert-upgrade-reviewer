#!/usr/bin/env python3
"""Compare risky function calls in changed Python files before/after a git diff.

This is a heuristic helper for migration review. It flags functions where lifecycle-ish
calls disappear or appear across a migration branch.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass, field

RISKY_NAMES = {
    "save", "close", "commit", "rollback", "flush", "execute", "connect", "dispose",
    "open", "read", "write", "delete", "update", "insert", "parse", "validate",
    "dict", "json", "model_dump", "model_validate", "raise_for_status",
}

LIFECYCLE_NAMES = {"close", "commit", "rollback", "flush", "dispose"}


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


def git_show(ref: str, path: str) -> str:
    try:
        return run(["git", "show", f"{ref}:{path}"])
    except subprocess.CalledProcessError:
        return ""


def changed_py_files(base: str, head: str) -> list[str]:
    out = run(["git", "diff", "--name-only", f"{base}...{head}"])
    return [line for line in out.splitlines() if line.endswith(".py")]


@dataclass
class FuncCalls:
    name: str
    lineno: int
    calls: list[str]


@dataclass
class FuncDiff:
    file: str
    function: str
    before_calls: list[str]
    after_calls: list[str]
    removed: list[str]
    added: list[str]
    lifecycle_removed: list[str]
    has_lifecycle_warning: bool


@dataclass
class DiffResult:
    base: str
    head: str
    changed_files: list[str] = field(default_factory=list)
    diffs: list[FuncDiff] = field(default_factory=list)

    @property
    def lifecycle_warnings(self) -> int:
        return sum(1 for d in self.diffs if d.has_lifecycle_warning)

    def to_json(self) -> str:
        return json.dumps(
            {
                "base": self.base,
                "head": self.head,
                "changed_files": self.changed_files,
                "diffs": [asdict(d) for d in self.diffs],
                "lifecycle_warnings": self.lifecycle_warnings,
            },
            indent=2,
        )

    def to_text(self) -> str:
        if not self.diffs:
            return "No changed Python files."
        lines: list[str] = []
        for d in self.diffs:
            lines.append(f"\n{d.file}::{d.function}")
            lines.append(f"  before risky calls: {' -> '.join(d.before_calls) if d.before_calls else '(none)'}")
            lines.append(f"  after risky calls:  {' -> '.join(d.after_calls) if d.after_calls else '(none)'}")
            if d.lifecycle_removed:
                lines.append(f"  WARNING: lifecycle calls removed: {', '.join(d.lifecycle_removed)}")
            elif d.removed:
                lines.append(f"  Note: risky calls removed: {', '.join(d.removed)}")
            if d.added:
                lines.append(f"  Note: risky calls added: {', '.join(d.added)}")
        lines.append(f"\nLifecycle warnings: {self.lifecycle_warnings}")
        return "\n".join(lines)


def call_name(node: object) -> str | None:
    import ast

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _collect_direct_calls(node: object) -> list[str]:
    import ast

    calls: list[str] = []

    def _walk(n: ast.AST) -> None:
        for child in ast.iter_child_nodes(n):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(child, ast.Call):
                name = call_name(child.func)
                if name in RISKY_NAMES:
                    calls.append(name)
            _walk(child)

    _walk(node)  # type: ignore[arg-type]
    return calls


def extract_calls(src: str) -> dict[str, FuncCalls]:
    import ast

    if not src.strip():
        return {}
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}

    result: dict[str, FuncCalls] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = _collect_direct_calls(node)
            key = f"{node.name}:{node.lineno}"
            result[key] = FuncCalls(node.name, node.lineno, calls)

    return result


def compare_calls(base: str, head: str) -> DiffResult:
    files = changed_py_files(base, head)
    result = DiffResult(base=base, head=head, changed_files=files)

    if not files:
        return result

    for path in files:
        before = extract_calls(git_show(base, path))
        after = extract_calls(git_show(head, path))
        all_func_names = sorted({v.name for v in before.values()} | {v.name for v in after.values()})

        for func_name in all_func_names:
            before_calls = []
            after_calls = []
            for v in before.values():
                if v.name == func_name:
                    before_calls.extend(v.calls)
            for v in after.values():
                if v.name == func_name:
                    after_calls.extend(v.calls)

            removed = sorted(set(before_calls) - set(after_calls))
            added = sorted(set(after_calls) - set(before_calls))
            lifecycle_removed = [x for x in removed if x in LIFECYCLE_NAMES]

            if removed or added:
                result.diffs.append(
                    FuncDiff(
                        file=path,
                        function=func_name,
                        before_calls=before_calls,
                        after_calls=after_calls,
                        removed=removed,
                        added=added,
                        lifecycle_removed=lifecycle_removed,
                        has_lifecycle_warning=bool(lifecycle_removed),
                    )
                )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--json", action="store_true", dest="output_json")
    args = parser.parse_args()

    base = args.base or detect_default_branch()

    result = compare_calls(base, args.head)

    if args.output_json:
        print(result.to_json())
    else:
        print(result.to_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())