from __future__ import annotations

import json
import subprocess

from scripts.dependency_diff import DEP_FILES, DepDiffResult, detect_default_branch, is_dep_file


class TestIsDepFile:
    def test_pyproject_toml(self):
        assert is_dep_file("pyproject.toml") is True

    def test_requirements_txt(self):
        assert is_dep_file("requirements.txt") is True

    def test_requirements_dev_txt(self):
        assert is_dep_file("requirements-dev.txt") is True

    def test_requirements_production_txt(self):
        assert is_dep_file("requirements-production.txt") is True

    def test_poetry_lock(self):
        assert is_dep_file("poetry.lock") is True

    def test_uv_lock(self):
        assert is_dep_file("uv.lock") is True

    def test_pipfile(self):
        assert is_dep_file("Pipfile") is True

    def test_pipfile_lock(self):
        assert is_dep_file("Pipfile.lock") is True

    def test_setup_py(self):
        assert is_dep_file("setup.py") is True

    def test_setup_cfg(self):
        assert is_dep_file("setup.cfg") is True

    def test_tox_ini(self):
        assert is_dep_file("tox.ini") is True

    def test_python_version(self):
        assert is_dep_file(".python-version") is True

    def test_unrelated_file(self):
        assert is_dep_file("main.py") is False

    def test_unrelated_md(self):
        assert is_dep_file("README.md") is False

    def test_unrelated_json(self):
        assert is_dep_file("package.json") is False

    def test_subdir_path(self):
        assert is_dep_file("src/pyproject.toml") is True

    def test_nested_requirements(self):
        assert is_dep_file("docker/requirements.txt") is True

    def test_partial_name_match(self):
        assert is_dep_file("my_requirements.txt") is False

    def test_exact_dep_file_list(self):
        assert DEP_FILES == (
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


class TestDepDiffResult:
    def test_to_json_with_diffs(self):
        result = DepDiffResult(
            base="main",
            head="HEAD",
            dep_files=["requirements.txt"],
            diffs={"requirements.txt": "--- a/requirements.txt\n+++ b/requirements.txt\n"},
        )
        data = json.loads(result.to_json())
        assert data["base"] == "main"
        assert data["head"] == "HEAD"
        assert data["dep_files"] == ["requirements.txt"]
        assert "--- a/requirements.txt" in data["diffs"]["requirements.txt"]

    def test_to_json_no_changes(self):
        result = DepDiffResult(base="main", head="HEAD")
        data = json.loads(result.to_json())
        assert data["dep_files"] == []
        assert data["diffs"] == {}

    def test_to_text_no_changes(self):
        result = DepDiffResult(base="main", head="HEAD")
        assert "No dependency/runtime files changed." in result.to_text()

    def test_to_text_with_changes(self):
        result = DepDiffResult(
            base="main",
            head="HEAD",
            dep_files=["pyproject.toml"],
            diffs={"pyproject.toml": "+requests>=2.28"},
        )
        text = result.to_text()
        assert "Dependency/runtime files changed:" in text
        assert "- pyproject.toml" in text
        assert "--- pyproject.toml ---" in text
        assert "+requests>=2.28" in text


class TestDetectDefaultBranch:
    def test_returns_string(self):
        result = detect_default_branch()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_does_not_raise(self):
        try:
            detect_default_branch()
        except subprocess.CalledProcessError:
            raise AssertionError("detect_default_branch should not raise")