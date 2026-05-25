"""Script generation pipeline using llama.cpp."""

import json
from typing import List, Optional

from pydantic import BaseModel


class Speaker(BaseModel):
    """Speaker identity in the script."""
    name: str
    role: str = "unknown"


class Scene(BaseModel):
    """A scene in the script with speaker actions."""
    speaker: str
    text: str
    description: Optional[str] = None


class ScriptChapter(BaseModel):
    """A chapter in the the script."""
    title: str
    scenes: List[Scene]


class Script(BaseModel):
    """Full script with all chapters."""
    title: str
    chapters: List[ScriptChapter]


class ScriptGenerator:
    """Generates structured scripts from lore text using llama.cpp."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 2048,
        n_threads: int = 4,
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._loaded = False

    def load(self) -> None:
        """Load the llama.cpp model."""
        if self._loaded:
            return
        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
            self._loaded = True
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Run: pip install llama-cpp-python"
            )

    def generate(self, lore_text: str, title: str = "Untitled Script") -> Script:
        """Generate a structured script from lore text."""
        if not self._loaded:
            self.load()
        prompt = self._build_prompt(lore_text, title)
        output = self._llm(prompt, max_tokens=2000, stop=["</s>", "###"])
        script_data = self._parse_output(output["choices"][0]["text"])
        return Script(title=title, **script_data)

    def _build_prompt(self, lore_text: str, title: str) -> str:
        schema = json.dumps({
            "title": "Script Title",
            "chapters": [{
                "title": "Chapter Title",
                "scenes": [{
                    "speaker": "Speaker Name",
                    "text": "Speaker's dialogue or action",
                    "description": "Optional scene description",
                }]
            }]
        }, indent=2)
        return (
            f"Extract a structured script from the following lore text.\n\n"
            f"Title: {title}\n\n"
            f"Lore Text:\n{lore_text[:4000]}\n\n"
            f"Output as JSON with this schema:\n{schema}\n\n"
            "Script JSON:"
        )

    def _parse_output(self, output: str) -> dict:
        try:
            start = output.find("{")
            end = output.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = output[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        return {
            "chapters": [{
                "title": "Untitled Chapter",
                "scenes": [{
                    "speaker": "Unknown",
                    "text": output[:200],
                    "description": "Generated from lore text",
                }]
            }]
        }
