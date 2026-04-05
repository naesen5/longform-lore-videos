from setuptools import setup, find_packages

setup(
    name="longform-lore-videos",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "moviepy>=2.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
        ],
    },
)
