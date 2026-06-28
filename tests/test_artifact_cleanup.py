import os
import tempfile
from core.artifact_cleanup import find_artifacts, cleanup_artifacts


def _touch(path):
    with open(path, "w") as f:
        f.write("test")


def test_find_artifacts_empty_dir():
    with tempfile.TemporaryDirectory() as tmp:
        results = find_artifacts(tmp)
        assert results == []


def test_find_artifacts_detects_bak():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "test.py.bak"))
        _touch(os.path.join(tmp, "normal.py"))
        results = find_artifacts(tmp)
        assert len(results) == 1
        assert results[0].endswith(".bak")


def test_find_artifacts_detects_optimized():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "agent_optimized.md"))
        _touch(os.path.join(tmp, "agent_optimized.json"))
        results = find_artifacts(tmp)
        assert len(results) == 2


def test_find_artifacts_detects_compiled_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "agent_compiled_prompt.txt"))
        results = find_artifacts(tmp)
        assert len(results) == 1


def test_find_artifacts_detects_section_comparison():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "agent_section_comparison.md"))
        results = find_artifacts(tmp)
        assert len(results) == 1


def test_find_artifacts_detects_generated_dataset():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "agent_generated_dataset.json"))
        results = find_artifacts(tmp)
        assert len(results) == 1


def test_find_artifacts_detects_report():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "optimization_report.md"))
        results = find_artifacts(tmp)
        assert len(results) == 1


def test_find_artifacts_skips_venv():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "venv"))
        _touch(os.path.join(tmp, "venv", "test.py.bak"))
        results = find_artifacts(tmp)
        assert len(results) == 0


def test_find_artifacts_skips_git():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, ".git"))
        _touch(os.path.join(tmp, ".git", "config.bak"))
        results = find_artifacts(tmp)
        assert len(results) == 0


def test_find_artifacts_recursive():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "subdir"))
        _touch(os.path.join(tmp, "subdir", "test.py.bak"))
        results = find_artifacts(tmp)
        assert len(results) == 1


def test_cleanup_artifacts_moves_files():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "test.py.bak"))
        _touch(os.path.join(tmp, "agent_optimized.md"))
        _touch(os.path.join(tmp, "normal.py"))

        result = cleanup_artifacts(tmp, archive_base=os.path.join(tmp, "custom_archive"))
        assert result["count"] == 2
        assert os.path.exists(result["archive_path"])
        assert os.path.isdir(result["archive_path"])
        # Verify originals are gone
        assert not os.path.exists(os.path.join(tmp, "test.py.bak"))
        assert not os.path.exists(os.path.join(tmp, "agent_optimized.md"))
        # Normal file should remain
        assert os.path.exists(os.path.join(tmp, "normal.py"))


def test_cleanup_artifacts_no_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        _touch(os.path.join(tmp, "normal.py"))
        _touch(os.path.join(tmp, "readme.md"))
        result = cleanup_artifacts(tmp)
        assert result["count"] == 0
        assert result["archive_path"] == ""
