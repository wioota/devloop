"""Snyk CLI installation helper for devloop init command."""

import os
import shutil
import subprocess
from typing import Tuple

import typer
from rich.console import Console

console = Console()


def check_snyk_available() -> Tuple[bool, str]:
    """Check if Snyk CLI is available.

    Returns:
        Tuple of (is_available, version_or_error)
    """
    snyk_path = shutil.which("snyk")
    if not snyk_path:
        return False, "Snyk CLI not found in PATH"

    try:
        result = subprocess.run(
            ["snyk", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, "Failed to get Snyk version"
    except Exception as e:
        return False, str(e)


def check_snyk_token() -> bool:
    """Check if SNYK_TOKEN environment variable is set.

    Returns:
        True if SNYK_TOKEN is set and non-empty
    """
    token = os.environ.get("SNYK_TOKEN", "").strip()
    return bool(token)


def install_snyk_cli() -> bool:
    """Install Snyk CLI globally using npm.

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        # Check if npm is available
        npm_path = shutil.which("npm")
        if not npm_path:
            console.print(
                "[red]✗[/red] npm not found. Please install Node.js and npm first."
            )
            console.print("  Visit: https://nodejs.org/")
            return False

        # Run npm install -g snyk
        console.print("  Installing Snyk CLI globally...")
        result = subprocess.run(
            ["npm", "install", "-g", "snyk"],
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes timeout for npm install
        )

        if result.returncode == 0:
            console.print("  [green]✓[/green] Snyk CLI installed successfully")
            return True
        else:
            console.print("[red]✗[/red] npm install failed:")
            console.print(f"  {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        console.print("[red]✗[/red] npm install timed out (>3 minutes)")
        return False
    except Exception as e:
        console.print(f"[red]✗[/red] Installation failed: {e}")
        return False


def authenticate_snyk() -> bool:
    """Authenticate Snyk CLI using SNYK_TOKEN environment variable.

    Returns:
        True if authentication succeeded, False otherwise
    """
    try:
        token = os.environ.get("SNYK_TOKEN", "").strip()
        if not token:
            console.print("[yellow]⚠[/yellow] SNYK_TOKEN environment variable not set")
            console.print(
                "  Set SNYK_TOKEN before running Snyk scans, or run 'snyk auth' manually"
            )
            return False

        # Authenticate using token
        console.print("  Authenticating Snyk CLI...")
        result = subprocess.run(
            ["snyk", "auth", token],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            console.print("  [green]✓[/green] Snyk CLI authenticated")
            return True
        else:
            console.print("[yellow]⚠[/yellow] Snyk authentication failed:")
            console.print(f"  {result.stderr}")
            console.print("  You can authenticate manually later with 'snyk auth'")
            return False

    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠[/yellow] Snyk auth timed out")
        return False
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Authentication failed: {e}")
        return False


def prompt_snyk_installation(non_interactive: bool = False) -> bool:
    """Prompt user to install Snyk CLI and perform installation.

    Args:
        non_interactive: If True, skip prompts and return success

    Returns:
        True if Snyk was installed/configured (or user declined), False on critical error
    """
    if non_interactive:
        return True  # Skip in non-interactive mode

    # Check if Snyk CLI is already installed
    snyk_available, snyk_info = check_snyk_available()

    if snyk_available:
        console.print(f"\n[green]✓[/green] Snyk CLI already installed: {snyk_info}")

        # Check authentication
        if check_snyk_token():
            if typer.confirm(
                "  Authenticate Snyk using SNYK_TOKEN environment variable?",
                default=True,
            ):
                authenticate_snyk()
        else:
            console.print(
                "  [yellow]Note:[/yellow] Set SNYK_TOKEN environment variable to authenticate"
            )
            console.print("  Or run 'snyk auth' manually later")

        return True

    # Snyk not installed - offer to install
    console.print("\n[yellow]Snyk CLI Installation[/yellow]")
    console.print(
        "Snyk CLI is not installed. It's required for security vulnerability scanning."
    )

    if typer.confirm("  Install Snyk CLI now using npm?", default=True):
        if install_snyk_cli():
            # Try to authenticate if token is available
            if check_snyk_token():
                authenticate_snyk()
            else:
                console.print(
                    "\n  [yellow]Next steps:[/yellow] Set SNYK_TOKEN environment variable and run 'snyk auth'"
                )
            return True
        else:
            console.print("\n  [yellow]You can install Snyk manually later:[/yellow]")
            console.print("    npm install -g snyk")
            console.print("    snyk auth")
            return False
    else:
        console.print("  Skipped Snyk CLI installation")
        console.print("  [yellow]Install later with:[/yellow] npm install -g snyk")
        return True
