"""Setup script for longform-lore-videos."""
from setuptools import setup, find_packages

setup(
    name="longform-lore-videos",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "diffusers>=0.36.0",
        "torchaudio>=2.0.0",
        "librosa>=0.11.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ]
    },
)
