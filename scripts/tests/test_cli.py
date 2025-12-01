#!/usr/bin/env python3
"""Test CLI to isolate the typer issue."""
from pathlib import Path
import typer

app = typer.Typer()


@app.command()
def init(
    path: Path = None,
    create_config: bool = True
):
    """Initialize claude-agents in a project."""
    if path is None:
        path = Path.cwd()
    print(f"Initializing in: {path}")
    print(f"Create config: {create_config}")


if __name__ == "__main__":
    app()
