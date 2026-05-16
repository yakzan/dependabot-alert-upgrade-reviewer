#!/usr/bin/env python3
"""Compare risky function calls in changed Python files before/after a git diff.

This is a heuristic helper for migration review. It flags functions where lifecycle-ish
calls disappear or appear across a migration branch.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
from dataclasses import dataclass

RISKY_NAMES = {
    "save", "close", "commit", "rollback", "flush", "execute", "connect", "dispose",
    "open", "read", "write", "delete", "update", "insert", "parse", "validate",
    "dict", "json", "model_dump", "model_validate", "raise_for_status",
}


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)


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


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _collect_direct_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Collect risky call names in a function body, skipping nested function defs."""
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

    _walk(node)
    return calls


def extract_calls(src: str) -> dict[str, FuncCalls]:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="main")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    files = changed_py_files(args.base, args.head)
    if not files:
        print("No changed Python files.")
        return 0

    warnings = 0
    for path in files:
        before = extract_calls(git_show(args.base, path))
        after = extract_calls(git_show(args.head, path))
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
            lifecycle_removed = [x for x in removed if x in {"close", "commit", "rollback", "flush", "dispose"}]

            if removed or added:
                print(f"\n{path}::{func_name}")
                print(f"  before risky calls: {' -> '.join(before_calls) if before_calls else '(none)'}")
                print(f"  after risky calls:  {' -> '.join(after_calls) if after_calls else '(none)'}")
                if lifecycle_removed:
                    print(f"  WARNING: lifecycle calls removed: {', '.join(lifecycle_removed)}")
                    warnings += 1
                elif removed:
                    print(f"  Note: risky calls removed: {', '.join(removed)}")
                if added:
                    print(f"  Note: risky calls added: {', '.join(added)}")

    print(f"\nLifecycle warnings: {warnings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
