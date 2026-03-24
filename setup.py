from setuptools import setup, find_packages

setup(
    name="MarketplaceBot",
    version="1.1.0",
    description="Auto-reply bot for Ozon/WB reviews",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pycryptodome",
    ],
    python_requires=">=3.8",
)

