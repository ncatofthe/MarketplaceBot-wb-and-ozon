from pathlib import Path
from setuptools import setup, find_packages


def load_requirements():
    requirements_file = Path(__file__).with_name("requirements.txt")
    if not requirements_file.exists():
        return []

    return [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="MarketplaceBot",
    version="1.1.0",
    description="Auto-reply bot for Ozon/WB reviews",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=load_requirements(),
    python_requires=">=3.8",
)

