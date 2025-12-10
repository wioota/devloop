"""DevLoop - Background agents for development workflow automation."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("devloop")
except PackageNotFoundError:
    __version__ = "0.0.0.dev"
