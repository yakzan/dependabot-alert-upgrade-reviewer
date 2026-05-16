from __future__ import annotations

import json
from pathlib import Path

from scripts.risky_patterns import PROFILES, DEFAULT_IGNORES, PatternHit, ScanResult, iter_py_files, scan_patterns


class TestProfiles:
    def test_profiles_exist(self):
        assert "lifecycle" in PROFILES
        assert "sqlalchemy" in PROFILES
        assert "pydantic" in PROFILES
        assert "pandas" in PROFILES
        assert "http" in PROFILES
        assert "pytest" in PROFILES
        assert "python-runtime" in PROFILES

    def test_profiles_are_valid_regex(self):
        import re

        for name, patterns in PROFILES.items():
            for p in patterns:
                re.compile(p)

    def test_default_ignores(self):
        assert ".git" in DEFAULT_IGNORES
        assert ".venv" in DEFAULT_IGNORES
        assert "node_modules" in DEFAULT_IGNORES
        assert "__pycache__" in DEFAULT_IGNORES


class TestIterPyFiles:
    def test_finds_py_files(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("x = 1")
        (tmp_path / "util.py").write_text("y = 2")
        result = list(iter_py_files(tmp_path))
        names = {p.name for p in result}
        assert names == {"app.py", "util.py"}

    def test_ignores_non_py_files(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("x = 1")
        (tmp_path / "readme.md").write_text("# hi")
        result = list(iter_py_files(tmp_path))
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_ignores_default_dirs(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("x = 1")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("z = 3")
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.cpython-310.pyc").write_text("bytecode")
        result = list(iter_py_files(tmp_path))
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_finds_nested_py_files(self, tmp_path: Path):
        subdir = tmp_path / "pkg"
        subdir.mkdir()
        (subdir / "mod.py").write_text("a = 1")
        (tmp_path / "top.py").write_text("b = 2")
        result = list(iter_py_files(tmp_path))
        names = {p.name for p in result}
        assert names == {"mod.py", "top.py"}

    def test_empty_dir(self, tmp_path: Path):
        result = list(iter_py_files(tmp_path))
        assert result == []


class TestScanPatterns:
    def test_finds_matching_pattern(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("session.query(User)\nengine.execute(stmt)\n")
        result = scan_patterns(tmp_path, [r"session\.query"])
        assert result.total == 1
        assert result.hits[0].pattern == r"session\.query"
        assert "session.query" in result.hits[0].content

    def test_multiple_profiles(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("commit()\nclose()\nread_csv('data.csv')\n")
        patterns = PROFILES["lifecycle"] + PROFILES["pandas"]
        result = scan_patterns(tmp_path, patterns)
        assert result.total >= 3

    def test_no_matches(self, tmp_path: Path):
        (tmp_path / "app.py").write_text("x = 1\ny = 2\n")
        result = scan_patterns(tmp_path, [r"nonexistent_pattern_xyz"])
        assert result.total == 0
        assert result.hits == []

    def test_python_runtime_skips_benign_collections_imports(self, tmp_path: Path):
        (tmp_path / "app.py").write_text(
            "from collections import OrderedDict, defaultdict, namedtuple, deque\n"
        )
        result = scan_patterns(tmp_path, PROFILES["python-runtime"])
        collections_hits = [h for h in result.hits if "from collections import" in h.pattern]
        assert collections_hits == []

    def test_python_runtime_flags_moved_abcs(self, tmp_path: Path):
        (tmp_path / "app.py").write_text(
            "from collections import Mapping, MutableMapping\n"
        )
        result = scan_patterns(tmp_path, PROFILES["python-runtime"])
        collections_hits = [h for h in result.hits if "from collections import" in h.pattern]
        assert len(collections_hits) >= 1


class TestScanResult:
    def test_to_json(self):
        result = ScanResult(hits=[
            PatternHit(file="a.py", line=1, pattern=r"commit\(", content="commit()"),
            PatternHit(file="b.py", line=5, pattern=r"close\(", content="conn.close()"),
        ])
        data = json.loads(result.to_json())
        assert data["total"] == 2
        assert len(data["hits"]) == 2
        assert data["hits"][0]["file"] == "a.py"
        assert data["hits"][0]["line"] == 1
        assert data["hits"][0]["pattern"] == r"commit\("
        assert data["hits"][1]["content"] == "conn.close()"

    def test_to_json_empty(self):
        result = ScanResult()
        data = json.loads(result.to_json())
        assert data["total"] == 0
        assert data["hits"] == []

    def test_to_text(self):
        result = ScanResult(hits=[
            PatternHit(file="a.py", line=1, pattern=r"commit\(", content="commit()"),
        ])
        text = result.to_text()
        assert "a.py:1: [commit\\(] commit()" in text
        assert "Total hits: 1" in text

    def test_to_text_empty(self):
        result = ScanResult()
        text = result.to_text()
        assert "Total hits: 0" in text

    def test_total_property(self):
        result = ScanResult(hits=[PatternHit(file="a.py", line=1, pattern="x", content="x")])
        assert result.total == 1