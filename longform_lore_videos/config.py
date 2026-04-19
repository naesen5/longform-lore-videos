"""Configuration and model validation for the longform-lore-videos pipeline."""

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Default model paths
MODELS_DIR = Path(__file__).parent.parent / "models"

# Required models and their SHA256 hashes (empty = no hash check)
REQUIRED_MODELS = {
    "whisper_base_en": {
        "path": MODELS_DIR / "ggml-base.en.bin",
        "description": "whisper.cpp base.en transcription model",
        "sha256": "",  # set after download
        "min_size": 140_000_000,  # ~142MB for base.en
    },
}

# Optional models
OPTIONAL_MODELS = {
    "sd_v1_5": {
        "path": MODELS_DIR / "sd-v1-5.safetensors",
        "description": "Stable Diffusion 1.5 model (~4.2GB)",
        "sha256": "",
        "min_size": 4_000_000_000,
    },
    "llama_model": {
        "path": MODELS_DIR / "llama-model.gguf",
        "description": "LLaMA GGUF model (user-specified)",
        "sha256": "",
        "min_size": 0,  # varies by model size
    },
}


def validate_models(required: bool = True) -> dict:
    """Validate that required models are present and correct.

    Args:
        required: If True, raise on missing required models.
                  If False, only log warnings.

    Returns:
        Dict with model status: {name: {"present": bool, "sha256_ok": bool, "size_ok": bool}}
    """
    results = {}

    # Check models directory exists
    if not MODELS_DIR.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        logger.warning("Created models directory: %s", MODELS_DIR)

    for name, spec in REQUIRED_MODELS.items():
        path = spec["path"]
        status = {"present": False, "sha256_ok": False, "size_ok": False}

        if not path.exists():
            logger.warning("Missing required model: %s (%s)", name, path)
            results[name] = status
            continue

        status["present"] = True

        # Check size
        file_size = path.stat().st_size
        status["size_ok"] = file_size >= spec["min_size"] if spec["min_size"] > 0 else True
        if not status["size_ok"]:
            logger.warning(
                "Model %s too small: %d bytes (min %d)", name, file_size, spec["min_size"]
            )

        # Check SHA256 if hash is configured
        if spec["sha256"]:
            actual_hash = _sha256_file(path)
            status["sha256_ok"] = actual_hash == spec["sha256"]
            if not status["sha256_ok"]:
                logger.error(
                    "SHA256 mismatch for %s: expected %s, got %s",
                    name, spec["sha256"], actual_hash,
                )

        results[name] = status

    # Check optional models (log only)
    for name, spec in OPTIONAL_MODELS.items():
        path = spec["path"]
        if path.exists():
            logger.info("Optional model present: %s (%s)", name, path)
        else:
            logger.info("Optional model not found: %s (%s) — will download on first use", name, path)

    return results


def _sha256_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def health_check() -> dict:
    """Full health check including models and tool availability.

    Returns:
        Dict suitable for JSON serialization in /health endpoint.
    """
    model_status = validate_models(required=False)

    tools = {
        "ffmpeg": _check_tool("ffmpeg"),
        "python": f"{'.'.join(str(x) for x in __import__('sys').version_info[:2])}",
    }

    # Check TTS availability
    try:
        import TTS  # noqa: F401
        tools["tts"] = "available"
    except ImportError:
        tools["tts"] = "not installed"

    # Check llama_cpp availability
    try:
        import llama_cpp  # noqa: F401
        tools["llama_cpp"] = f"v{llama_cpp.__version__}"
    except ImportError:
        tools["llama_cpp"] = "not installed"

    # Check stable_diffusion_cpp availability
    try:
        import stable_diffusion_cpp  # noqa: F401
        tools["stable_diffusion_cpp"] = "available"
    except ImportError:
        tools["stable_diffusion_cpp"] = "not installed"

    return {
        "models": model_status,
        "tools": tools,
        "models_dir": str(MODELS_DIR),
    }


def _check_tool(name: str) -> str:
    """Check if a CLI tool is available on PATH."""
    import shutil
    if shutil.which(name):
        return "available"
    return "not found"
