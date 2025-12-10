#!/usr/bin/env python3
"""Bump version across all files consistently."""
import re
import sys
from pathlib import Path


def validate_version(version: str) -> bool:
    """Validate semantic version format."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))


def bump_version(new_version: str):
    """Update version in all locations."""
    if not validate_version(new_version):
        print(f"ERROR: Invalid version format: {new_version}")
        print("Expected format: MAJOR.MINOR.PATCH (e.g., 0.3.4)")
        sys.exit(1)

    files_to_update = {
        "pyproject.toml": (
            r'^version = "\d+\.\d+\.\d+"',
            f'version = "{new_version}"'
        ),
    }

    # Verify all files exist
    for file_path in files_to_update.keys():
        if not Path(file_path).exists():
            print(f"ERROR: File not found: {file_path}")
            print("Run this script from the project root directory.")
            sys.exit(1)

    # Update all files
    for file_path, (pattern, replacement) in files_to_update.items():
        path = Path(file_path)
        content = path.read_text()
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content == new_content:
            print(f"⚠ No changes made to {file_path} (pattern not found)")
        else:
            path.write_text(new_content)
            print(f"✓ Updated {file_path}")

    print(f"\n✓ Version bumped to {new_version}")
    print("\nNext steps:")
    print("  git add pyproject.toml")
    print(f"  git commit -m 'chore: Bump version to {new_version}'")
    print(f"  git tag -a v{new_version} -m 'Release v{new_version}'")
    print(f"  git push origin main v{new_version}")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump-version.py <version>")
        print("Example: python scripts/bump-version.py 0.3.4")
        sys.exit(1)

    bump_version(sys.argv[1])


if __name__ == "__main__":
    main()
