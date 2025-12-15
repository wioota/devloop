"""CodeRabbit CLI installation helper for devloop init command."""

import os
import shutil
import subprocess
from typing import Tuple

import typer
from rich.console import Console

console = Console()


def check_coderabbit_available() -> Tuple[bool, str]:
    """Check if CodeRabbit CLI is available.

    Returns:
        Tuple of (is_available, version_or_error)
    """
    coderabbit_path = shutil.which("coderabbit")
    if not coderabbit_path:
        return False, "CodeRabbit CLI not found in PATH"

    try:
        result = subprocess.run(
            ["coderabbit", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, "Failed to get CodeRabbit version"
    except Exception as e:
        return False, str(e)


def check_coderabbit_api_key() -> bool:
    """Check if CODE_RABBIT_API_KEY environment variable is set.

    Returns:
        True if CODE_RABBIT_API_KEY is set and non-empty
    """
    api_key = os.environ.get("CODE_RABBIT_API_KEY", "").strip()
    return bool(api_key)


def install_coderabbit_cli() -> bool:
    """Install CodeRabbit CLI using the official installer script.

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        # Check if curl is available
        curl_path = shutil.which("curl")
        if not curl_path:
            console.print("[red]✗[/red] curl not found. Please install curl first.")
            return False

        # Check if sh is available
        sh_path = shutil.which("sh")
        if not sh_path:
            console.print("[red]✗[/red] sh shell not found.")
            return False

        # Run the CodeRabbit installer
        console.print("  Installing CodeRabbit CLI...")
        console.print("  Running: curl -fsSL https://cli.coderabbit.ai/install.sh | sh")

        # Download and run installer
        result = subprocess.run(
            ["sh", "-c", "curl -fsSL https://cli.coderabbit.ai/install.sh | sh"],
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutes timeout
        )

        if result.returncode == 0:
            console.print("  [green]✓[/green] CodeRabbit CLI installed successfully")
            return True
        else:
            console.print("[red]✗[/red] Installation failed:")
            if result.stderr:
                console.print(f"  {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        console.print("[red]✗[/red] Installation timed out (>3 minutes)")
        return False
    except Exception as e:
        console.print(f"[red]✗[/red] Installation failed: {e}")
        return False


def authenticate_coderabbit() -> bool:
    """Authenticate CodeRabbit CLI.

    CodeRabbit CLI uses CODE_RABBIT_API_KEY environment variable for authentication.
    The 'coderabbit auth' command may be used for interactive authentication.

    Returns:
        True if authentication is configured, False otherwise
    """
    try:
        api_key = os.environ.get("CODE_RABBIT_API_KEY", "").strip()
        if not api_key:
            console.print(
                "[yellow]⚠[/yellow] CODE_RABBIT_API_KEY environment variable not set"
            )
            console.print("  Set CODE_RABBIT_API_KEY before running CodeRabbit scans")
            console.print("  Or run 'coderabbit auth' for interactive authentication")
            return False

        console.print("  [green]✓[/green] CODE_RABBIT_API_KEY is configured")
        return True

    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Authentication check failed: {e}")
        return False


def prompt_coderabbit_installation(non_interactive: bool = False) -> bool:
    """Prompt user to install CodeRabbit CLI and perform installation.

    Args:
        non_interactive: If True, skip prompts and return success

    Returns:
        True if CodeRabbit was installed/configured (or user declined), False on critical error
    """
    if non_interactive:
        return True  # Skip in non-interactive mode

    # Check if CodeRabbit CLI is already installed
    coderabbit_available, coderabbit_info = check_coderabbit_available()

    if coderabbit_available:
        console.print(
            f"\n[green]✓[/green] CodeRabbit CLI already installed: {coderabbit_info}"
        )

        # Check authentication
        if not check_coderabbit_api_key():
            console.print(
                "  [yellow]Note:[/yellow] Set CODE_RABBIT_API_KEY environment variable to authenticate"
            )
            console.print("  Or run 'coderabbit auth' manually later")
        else:
            authenticate_coderabbit()

        return True

    # CodeRabbit not installed - offer to install
    console.print("\n[yellow]CodeRabbit CLI Installation[/yellow]")
    console.print(
        "CodeRabbit CLI is not installed. It's required for AI-powered code analysis."
    )

    if typer.confirm(
        "  Install CodeRabbit CLI now using the official installer?", default=True
    ):
        if install_coderabbit_cli():
            # Check authentication
            if not check_coderabbit_api_key():
                console.print(
                    "\n  [yellow]Next steps:[/yellow] Set CODE_RABBIT_API_KEY environment variable"
                )
                console.print(
                    "  Or run 'coderabbit auth' for interactive authentication"
                )
            else:
                authenticate_coderabbit()
            return True
        else:
            console.print(
                "\n  [yellow]You can install CodeRabbit manually later:[/yellow]"
            )
            console.print("    curl -fsSL https://cli.coderabbit.ai/install.sh | sh")
            console.print("    coderabbit auth")
            return False
    else:
        console.print("  Skipped CodeRabbit CLI installation")
        console.print(
            "  [yellow]Install later with:[/yellow] curl -fsSL https://cli.coderabbit.ai/install.sh | sh"
        )
        return True
