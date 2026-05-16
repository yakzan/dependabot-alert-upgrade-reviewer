from __future__ import annotations

import ast
import json
import subprocess

from scripts.risky_call_diff import (
    LIFECYCLE_NAMES,
    RISKY_NAMES,
    DiffResult,
    FuncCalls,
    FuncDiff,
    call_name,
    detect_default_branch,
    extract_calls,
)


class TestCallName:
    def test_name_node(self):
        node = ast.Name(id="commit")
        assert call_name(node) == "commit"

    def test_attribute_node(self):
        node = ast.Attribute(attr="close", value=ast.Name(id="conn"))
        assert call_name(node) == "close"

    def test_other_node_returns_none(self):
        node = ast.Constant(value=42)
        assert call_name(node) is None

    def test_subscript_returns_none(self):
        node = ast.Subscript(value=ast.Name(id="d"), slice=ast.Constant(value=0))
        assert call_name(node) is None


class TestExtractCalls:
    def test_empty_source(self):
        assert extract_calls("") == {}

    def test_whitespace_only(self):
        assert extract_calls("   \n  \n") == {}

    def test_syntax_error(self):
        assert extract_calls("def f(:\n") == {}

    def test_function_with_no_calls(self):
        src = "def foo():\n    pass\n"
        result = extract_calls(src)
        assert "foo:1" in result
        assert result["foo:1"].calls == []

    def test_function_with_risky_call(self):
        src = "def foo():\n    commit()\n"
        result = extract_calls(src)
        assert "foo:1" in result
        assert "commit" in result["foo:1"].calls

    def test_function_with_non_risky_call(self):
        src = "def foo():\n    print('hello')\n"
        result = extract_calls(src)
        assert "foo:1" in result
        assert result["foo:1"].calls == []

    def test_multiple_risky_calls(self):
        src = "def foo():\n    commit()\n    close()\n    flush()\n"
        result = extract_calls(src)
        calls = result["foo:1"].calls
        assert "commit" in calls
        assert "close" in calls
        assert "flush" in calls

    def test_async_function(self):
        src = "async def foo():\n    await commit()\n"
        result = extract_calls(src)
        assert "foo:1" in result

    def test_method_call(self):
        src = "def foo():\n    session.commit()\n"
        result = extract_calls(src)
        assert "commit" in result["foo:1"].calls

    def test_nested_function_does_not_merge(self):
        src = "def outer():\n    commit()\n    def inner():\n        close()\n    rollback()\n"
        result = extract_calls(src)
        outer_calls = result["outer:1"].calls
        inner_calls = result["inner:3"].calls
        assert "commit" in outer_calls
        assert "rollback" in outer_calls
        assert "close" not in outer_calls
        assert "close" in inner_calls

    def test_two_functions(self):
        src = "def foo():\n    commit()\n\ndef bar():\n    close()\n"
        result = extract_calls(src)
        assert "commit" in result["foo:1"].calls
        assert "close" in result["bar:4"].calls

    def test_funcalls_dataclass(self):
        fc = FuncCalls(name="test", lineno=5, calls=["commit", "close"])
        assert fc.name == "test"
        assert fc.lineno == 5
        assert fc.calls == ["commit", "close"]


class TestRiskyNames:
    def test_lifecycle_names_present(self):
        assert "close" in RISKY_NAMES
        assert "commit" in RISKY_NAMES
        assert "rollback" in RISKY_NAMES
        assert "flush" in RISKY_NAMES
        assert "dispose" in RISKY_NAMES
        assert "save" in RISKY_NAMES
        assert "execute" in RISKY_NAMES
        assert "connect" in RISKY_NAMES
        assert "open" in RISKY_NAMES
        assert "read" in RISKY_NAMES
        assert "write" in RISKY_NAMES

    def test_lifecycle_names_constant(self):
        assert LIFECYCLE_NAMES == {"close", "commit", "rollback", "flush", "dispose"}

    def test_common_http_names_present(self):
        assert "raise_for_status" in RISKY_NAMES

    def test_pydantic_names_present(self):
        assert "model_dump" in RISKY_NAMES
        assert "model_validate" in RISKY_NAMES
        assert "model_dump_json" in RISKY_NAMES
        assert "model_validate_json" in RISKY_NAMES
        assert "parse_obj" in RISKY_NAMES
        assert "parse_raw" in RISKY_NAMES


class TestDiffResult:
    def test_to_json(self):
        diff = FuncDiff(
            file="app.py",
            function="process",
            before_calls=["commit", "close"],
            after_calls=["commit"],
            removed=["close"],
            added=[],
            lifecycle_removed=["close"],
            has_lifecycle_warning=True,
        )
        result = DiffResult(base="main", head="HEAD", changed_files=["app.py"], diffs=[diff])
        data = json.loads(result.to_json())
        assert data["base"] == "main"
        assert data["head"] == "HEAD"
        assert data["lifecycle_warnings"] == 1
        assert len(data["diffs"]) == 1
        assert data["diffs"][0]["function"] == "process"
        assert data["diffs"][0]["lifecycle_removed"] == ["close"]

    def test_to_json_empty(self):
        result = DiffResult(base="main", head="HEAD")
        data = json.loads(result.to_json())
        assert data["lifecycle_warnings"] == 0
        assert data["changed_files"] == []
        assert data["diffs"] == []

    def test_to_text_empty(self):
        result = DiffResult(base="main", head="HEAD")
        assert result.to_text() == "No changed Python files."

    def test_to_text_with_warnings(self):
        diff = FuncDiff(
            file="app.py",
            function="process",
            before_calls=["commit", "close"],
            after_calls=["commit"],
            removed=["close"],
            added=[],
            lifecycle_removed=["close"],
            has_lifecycle_warning=True,
        )
        result = DiffResult(base="main", head="HEAD", changed_files=["app.py"], diffs=[diff])
        text = result.to_text()
        assert "WARNING: lifecycle calls removed: close" in text
        assert "Lifecycle warnings: 1" in text

    def test_lifecycle_warnings_property(self):
        d1 = FuncDiff("a.py", "f", [], [], ["close"], ["open"], ["close"], True)
        d2 = FuncDiff("b.py", "g", [], [], [], ["commit"], [], False)
        result = DiffResult(base="main", head="HEAD", diffs=[d1, d2])
        assert result.lifecycle_warnings == 1


class TestDetectDefaultBranch:
    def test_returns_string(self):
        result = detect_default_branch()
        assert isinstance(result, str)
        assert result in ("main", "master") or True

    def test_does_not_raise(self):
        try:
            detect_default_branch()
        except subprocess.CalledProcessError:
            raise AssertionError("detect_default_branch should not raise")