"""Pyodide sandbox installation helper for devloop init command."""

import shutil
import subprocess
from pathlib import Path
from typing import Tuple

from rich.console import Console

console = Console()


def check_node_available() -> Tuple[bool, str]:
    """Check if Node.js is available.

    Returns:
        Tuple of (is_available, version_or_error)
    """
    node_path = shutil.which("node")
    if not node_path:
        return False, "Node.js not found in PATH"

    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, "Failed to get Node.js version"
    except Exception as e:
        return False, str(e)


def install_pyodide() -> bool:
    """Install Pyodide npm package in devloop security module.

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        # Get security module directory
        import devloop.security

        security_dir = Path(devloop.security.__file__).parent

        # Check if package.json exists
        package_json = security_dir / "package.json"
        if not package_json.exists():
            console.print("[red]✗[/red] package.json not found in security module")
            return False

        # Run npm install
        console.print(f"  Installing Pyodide in {security_dir}...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=security_dir,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout for npm install
        )

        if result.returncode == 0:
            console.print("  [green]✓[/green] Pyodide installed successfully")
            return True
        else:
            console.print("[red]✗[/red] npm install failed:")
            console.print(f"  {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        console.print("[red]✗[/red] npm install timed out (>5 minutes)")
        return False
    except Exception as e:
        console.print(f"[red]✗[/red] Installation failed: {e}")
        return False


def prompt_pyodide_installation(non_interactive: bool = False) -> bool:
    """Prompt user to install Pyodide and perform installation.

    Args:
        non_interactive: If True, skip prompts

    Returns:
        True if Pyodide was installed (or user declined), False on error
    """
    if non_interactive:
        return True  # Skip in non-interactive mode

    # Check if Node.js is available
    node_available, node_info = check_node_available()

    if not node_available:
        console.print(
            "\n[yellow]Note:[/yellow] Pyodide WASM sandbox requires Node.js 18+"
        )
        console.print(f"  Node.js status: {node_info}")
        console.print("  Install Node.js from https://nodejs.org/ to enable Pyodide")
        console.print("  [dim]DevLoop will work without it (using POC mode)[/dim]\n")
        return True  # Not an error, just not available

    # Node.js is available
    console.print("\n[cyan]Pyodide WASM Sandbox Setup[/cyan]")
    console.print(f"  Node.js {node_info} detected")
    console.print("  Pyodide enables cross-platform Python code sandboxing in WASM")

    import typer

    if typer.confirm(
        "\nInstall [yellow]Pyodide[/yellow] for enhanced sandbox security?",
        default=True,
    ):
        success = install_pyodide()
        if success:
            console.print(
                "  [green]✓[/green] Pyodide sandbox enabled for cross-platform support"
            )
        else:
            console.print(
                "  [yellow]⚠[/yellow] Pyodide installation failed, using POC mode"
            )
        return success
    else:
        console.print(
            "  [dim]Skipped Pyodide installation (POC mode will be used)[/dim]"
        )
        return True  # User declined, not an error
