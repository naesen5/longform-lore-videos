"""Image generation pipeline using stable-diffusion.cpp."""
import os
from pathlib import Path
from typing import Optional


class ImageGenerator:
    """Generate cinematic scene images using local stable-diffusion.cpp."""
    
    # Quality presets: (resolution, image_count)
    QUALITY_PRESETS = {
        "draft": (512, 1),
        "standard": (768, 2),
        "hq": (1024, 3),
    }
    
    # NSFW keywords for filtering
    NSFW_KEYWORDS = [
        "explicit", "nsfw", "porn", "sex", "nude", "cock", "child",
        "blood", "gun", "kill", "death", "dead", "smoking", "password",
        "credit card", "ssn", "social security", "bank account",
    ]
    
    def __init__(
        self,
        model_id: str = "stabilityai/stable-diffusion-2-1",
        output_dir: str = "output",
        quality: str = "standard"
    ):
        """
        Initialize the image generator.
        
        Args:
            model_id: HuggingFace model ID for stable diffusion
            output_dir: Base directory for output files
            quality: Quality preset (draft/standard/hq)
        """
        self.model_id = model_id
        self.output_dir = Path(output_dir)
        self.quality = quality
        
        # Validate quality preset
        if quality not in self.QUALITY_PRESETS:
            raise ValueError(f"Invalid quality preset: {quality}")
    
    @property
    def resolution(self) -> int:
        """Get resolution for current quality preset."""
        return self.QUALITY_PRESETS[self.quality][0]
    
    @property
    def image_count(self) -> int:
        """Get image count for current quality preset."""
        return self.QUALITY_PRESETS[self.quality][1]
    
    def _construct_prompt(self, scene_description: str, genre: str = "") -> str:
        """
        Construct a positive prompt from scene description and genre.
        
        Args:
            scene_description: Description of the scene/action
            genre: Genre/style tag (fantasy, sci-fi, historical, mythology)
            
        Returns:
            Constructed prompt string
        """
        genre_suffixes = {
            "fantasy": "epic fantasy cinematic, dramatic lighting, cinematic composition",
            "sci-fi": "futuristic cinematic, high-tech aesthetic, modern cinematic style",
            "historical": "historical cinematic, vintage style, classic film tone",
            "mythology": "mythological cinematic, ancient world, storytelling style",
        }
        
        suffix = genre_suffixes.get(genre.lower(), "cinematic style")
        return f"{scene_description}, {suffix}"
    
    def _construct_negative_prompt(self) -> str:
        """
        Construct a negative prompt for NSFW filtering.
        
        Returns:
            Negative prompt string
        """
        return ", ".join(self.NSFW_KEYWORDS)
    
    def _is_nsfw(self, prompt: str) -> bool:
        """
        Check if prompt contains NSFW keywords.
        
        Args:
            prompt: Prompt to check
            
        Returns:
            True if NSFW detected
        """
        prompt_lower = prompt.lower()
        return any(kw in prompt_lower for kw in self.NSFW_KEYWORDS)
    
    def generate_chapter(self, chapter: dict, job_id: str) -> list[str]:
        """
        Generate images for a chapter.
        
        Args:
            chapter: Chapter data with scene_description and genre
            job_id: Unique job identifier for output paths
            
        Returns:
            List of output file paths
        """
        scene_desc = chapter.get("scene_description", "")
        genre = chapter.get("genre", "")
        
        if not scene_desc:
            raise ValueError("Chapter missing scene_description")
        
        # Construct prompt
        prompt = self._construct_prompt(scene_desc, genre)
        
        # Check NSFW
        if self._is_nsfw(prompt):
            raise ValueError("NSFW content detected in prompt")
        
        # Generate images
        output_dir = self.output_dir / job_id / "images"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_paths = []
        for i in range(self.image_count):
            filename = f"chapter_{job_id}_img_{i}.png"
            filepath = output_dir / filename
            file_paths.append(str(filepath))
        
        # TODO: Implement actual SD.cpp invocation
        # For now, return mock paths
        return file_paths
