"""Setup configuration for pip installation."""
from setuptools import find_packages, setup

setup(
    name="devloop",
    version="0.2.0",
    description="Background agents for development workflow automation",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.5",
        "watchdog>=3.0",
        "typer>=0.9",
        "rich>=13.7",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4",
            "pytest-asyncio>=0.21",
            "black>=23.12",
            "ruff>=0.1",
        ]
    },
    entry_points={
        "console_scripts": [
            "devloop=devloop.cli.main:app",
        ],
    },
)
