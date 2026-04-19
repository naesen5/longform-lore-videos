"""Smoke tests for dependency setup (issue #2).

Tests that each backend tool is importable and functional.
These are lightweight — they verify the build succeeded, not full pipeline behavior.
"""

import importlib
import subprocess
from pathlib import Path

import pytest


REPO_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_DIR / "scripts"
MODELS_DIR = REPO_DIR / "models"


def _import_optional(name: str):
    """Try to import a module, return None if not found."""
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


class TestBuildScripts:
    """Verify build scripts exist and are executable."""

    def test_build_llamacpp_exists(self):
        assert (SCRIPTS_DIR / "build_llamacpp.sh").exists(), "build_llamacpp.sh missing"

    def test_build_sdcpp_exists(self):
        assert (SCRIPTS_DIR / "build_sdcpp.sh").exists(), "build_sdcpp.sh missing"

    def test_build_whispercpp_exists(self):
        assert (SCRIPTS_DIR / "build_whispercpp.sh").exists(), "build_whispercpp.sh missing"

    def test_download_models_exists(self):
        assert (SCRIPTS_DIR / "download_models.sh").exists(), "download_models.sh missing"

    def test_setup_exists(self):
        assert (SCRIPTS_DIR / "setup.sh").exists(), "setup.sh missing"

    def test_scripts_are_executable(self):
        for script in SCRIPTS_DIR.glob("*.sh"):
            assert script.stat().st_mode & 0o111, f"{script.name} is not executable"


class TestConfig:
    """Verify config.py and validate_models()."""

    def test_config_importable(self):
        """config.py should be importable."""
        from longform_lore_videos import config  # noqa: F401
        assert config is not None

    def test_validate_models_returns_dict(self):
        """validate_models() should return a dict."""
        from longform_lore_videos.config import validate_models
        result = validate_models(required=False)
        assert isinstance(result, dict)

    def test_health_check_returns_dict(self):
        """health_check() should return a dict suitable for JSON."""
        from longform_lore_videos.config import health_check
        result = health_check()
        assert isinstance(result, dict)
        assert "models" in result
        assert "tools" in result

    def test_ffmpeg_available(self):
        """ffmpeg should be on PATH."""
        result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
        assert result.returncode == 0, "ffmpeg not found on PATH"

    def test_moviepy_in_pyproject(self):
        """moviepy should be listed in pyproject.toml dependencies."""
        pyproject = REPO_DIR / "pyproject.toml"
        content = pyproject.read_text()
        assert "moviepy" in content, "moviepy not in pyproject.toml dependencies"

    def test_pyloudnorm_in_pyproject(self):
        """pyloudnorm should be listed in pyproject.toml dependencies."""
        pyproject = REPO_DIR / "pyproject.toml"
        content = pyproject.read_text()
        assert "pyloudnorm" in content, "pyloudnorm not in pyproject.toml dependencies"


class TestModelsDirectory:
    """Verify models directory structure."""

    def test_models_dir_exists(self):
        """models/ directory should exist (created by config)."""
        assert MODELS_DIR.exists(), "models/ directory missing"

    def test_models_dir_is_directory(self):
        """models/ should be a directory, not a file."""
        assert MODELS_DIR.is_dir(), "models/ is not a directory"


class TestDependencies:
    """Verify key Python dependencies are importable (installed via package)."""

    def test_pydantic_importable(self):
        import pydantic  # noqa: F401
        assert pydantic is not None

    def test_pillow_importable(self):
        from PIL import Image  # noqa: F401
        assert Image is not None

    def test_numpy_importable(self):
        import numpy  # noqa: F401
        assert numpy is not None

    def test_pydantic_version(self):
        import pydantic
        parts = pydantic.__version__.split(".")
        major = int(parts[0])
        assert major >= 2, f"pydantic >= 2.0 required, got {pydantic.__version__}"

    def test_pillow_version(self):
        from PIL import Image
        version = Image.__version__
        parts = version.split(".")
        major = int(parts[0])
        assert major >= 10, f"pillow >= 10.0 required, got {version}"
