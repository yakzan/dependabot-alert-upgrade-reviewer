from __future__ import annotations

from pathlib import Path

from scripts.risky_patterns import PROFILES, DEFAULT_IGNORES, iter_py_files


class TestProfiles:
    def test_profiles_exist(self):
        assert "lifecycle" in PROFILES
        assert "sqlalchemy" in PROFILES
        assert "pydantic" in PROFILES
        assert "pandas" in PROFILES
        assert "http" in PROFILES

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