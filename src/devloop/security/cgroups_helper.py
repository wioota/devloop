"""cgroups v2 integration for resource limit enforcement.

Provides memory and CPU limits for sandboxed processes using Linux cgroups.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class CgroupsResources:
    """Resource usage measured from cgroups.

    Attributes:
        memory_peak_mb: Peak memory usage in megabytes
        cpu_usage_percent: CPU usage percentage
    """

    memory_peak_mb: float
    cpu_usage_percent: float


class CgroupsManager:
    """Manager for cgroups v2 resource limits.

    Provides:
    - Memory limits (memory.max)
    - CPU limits (cpu.max)
    - Resource usage tracking
    """

    def __init__(self, cgroup_name: str = "devloop-agents"):
        """Initialize cgroups manager.

        Args:
            cgroup_name: Name of the cgroup to create
        """
        self.cgroup_name = cgroup_name
        self.logger = logging.getLogger("sandbox.cgroups")
        self._cgroup_path: Optional[Path] = None
        self._available: Optional[bool] = None

    async def is_available(self) -> bool:
        """Check if cgroups v2 is available.

        Returns:
            True if cgroups v2 is mounted and usable
        """
        if self._available is not None:
            return self._available

        # Check if cgroups v2 is mounted
        cgroup_mount = Path("/sys/fs/cgroup")
        if not cgroup_mount.exists():
            self.logger.warning("cgroups v2 not mounted at /sys/fs/cgroup")
            self._available = False
            return False

        # Check for cgroup.controllers (cgroups v2 indicator)
        controllers_file = cgroup_mount / "cgroup.controllers"
        if not controllers_file.exists():
            self.logger.warning("cgroups v2 controllers file not found")
            self._available = False
            return False

        # Check if we have required controllers
        try:
            controllers = controllers_file.read_text().strip().split()
            if "memory" not in controllers or "cpu" not in controllers:
                self.logger.warning(
                    f"Required controllers not available. Found: {controllers}"
                )
                self._available = False
                return False
        except (OSError, PermissionError) as e:
            self.logger.warning(f"Cannot read cgroup controllers: {e}")
            self._available = False
            return False

        self._available = True
        return True

    def _get_cgroup_path(self) -> Path:
        """Get or create cgroup path.

        Returns:
            Path to cgroup directory

        Raises:
            RuntimeError: If cgroups not available or creation fails
        """
        if self._cgroup_path is not None:
            return self._cgroup_path

        base_path = Path("/sys/fs/cgroup")
        cgroup_path = base_path / self.cgroup_name

        # Create cgroup if it doesn't exist
        if not cgroup_path.exists():
            try:
                cgroup_path.mkdir(parents=True, exist_ok=True)
                # Enable memory and cpu controllers
                subtree_control = base_path / "cgroup.subtree_control"
                if subtree_control.exists():
                    subprocess.run(
                        ["sh", "-c", f"echo '+memory +cpu' > {subtree_control}"],
                        check=True,
                        capture_output=True,
                    )
            except (OSError, subprocess.CalledProcessError) as e:
                raise RuntimeError(f"Failed to create cgroup: {e}")

        self._cgroup_path = cgroup_path
        return cgroup_path

    def set_memory_limit(self, max_memory_mb: int) -> None:
        """Set memory limit for cgroup.

        Args:
            max_memory_mb: Maximum memory in megabytes

        Raises:
            RuntimeError: If cgroups not available or setting fails
        """
        cgroup_path = self._get_cgroup_path()
        memory_max = cgroup_path / "memory.max"

        try:
            # Convert MB to bytes
            max_bytes = max_memory_mb * 1024 * 1024
            memory_max.write_text(str(max_bytes))
            self.logger.debug(f"Set memory limit to {max_memory_mb}MB")
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Failed to set memory limit: {e}")

    def set_cpu_limit(self, max_cpu_percent: int) -> None:
        """Set CPU limit for cgroup.

        Args:
            max_cpu_percent: Maximum CPU usage percentage (0-100)

        Raises:
            RuntimeError: If cgroups not available or setting fails
        """
        cgroup_path = self._get_cgroup_path()
        cpu_max = cgroup_path / "cpu.max"

        try:
            # cpu.max format: "$MAX $PERIOD"
            # Period is typically 100000 (100ms)
            # Max is quota in microseconds per period
            period = 100000
            quota = int((max_cpu_percent / 100.0) * period)
            cpu_max.write_text(f"{quota} {period}")
            self.logger.debug(f"Set CPU limit to {max_cpu_percent}%")
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Failed to set CPU limit: {e}")

    def add_process(self, pid: int) -> None:
        """Add process to cgroup.

        Args:
            pid: Process ID to add

        Raises:
            RuntimeError: If cgroups not available or adding fails
        """
        cgroup_path = self._get_cgroup_path()
        procs_file = cgroup_path / "cgroup.procs"

        try:
            procs_file.write_text(str(pid))
            self.logger.debug(f"Added process {pid} to cgroup")
        except (OSError, PermissionError) as e:
            raise RuntimeError(f"Failed to add process to cgroup: {e}")

    def get_resource_usage(self) -> CgroupsResources:
        """Get current resource usage from cgroup.

        Returns:
            Resource usage measurements

        Raises:
            RuntimeError: If cgroups not available or reading fails
        """
        cgroup_path = self._get_cgroup_path()

        try:
            # Read memory usage
            memory_current = cgroup_path / "memory.current"
            memory_bytes = int(memory_current.read_text().strip())
            memory_mb = memory_bytes / (1024 * 1024)

            # Read CPU usage (simplified - actual usage tracking is complex)
            # cpu.stat contains usage_usec
            cpu_stat = cgroup_path / "cpu.stat"
            _cpu_usage_usec = 0
            for line in cpu_stat.read_text().strip().split("\n"):
                if line.startswith("usage_usec"):
                    _cpu_usage_usec = int(line.split()[1])
                    break

            # Convert to percentage (simplified - would need delta over time)
            # For now, just return 0 as placeholder
            cpu_percent = 0.0

            return CgroupsResources(
                memory_peak_mb=memory_mb, cpu_usage_percent=cpu_percent
            )

        except (OSError, ValueError) as e:
            self.logger.warning(f"Failed to read resource usage: {e}")
            return CgroupsResources(memory_peak_mb=0.0, cpu_usage_percent=0.0)

    def cleanup(self) -> None:
        """Remove cgroup.

        Best effort cleanup - doesn't raise errors.
        """
        if self._cgroup_path and self._cgroup_path.exists():
            try:
                # Remove all processes first
                procs_file = self._cgroup_path / "cgroup.procs"
                if procs_file.exists():
                    pids = procs_file.read_text().strip().split("\n")
                    # Processes should have exited, but ensure empty
                    if pids and pids[0]:
                        self.logger.warning(f"Cgroup still has processes: {pids}")

                # Remove cgroup directory
                self._cgroup_path.rmdir()
                self.logger.debug("Cleaned up cgroup")
            except (OSError, PermissionError) as e:
                self.logger.warning(f"Failed to cleanup cgroup: {e}")


# Global singleton
_cgroups_manager: Optional[CgroupsManager] = None


def get_cgroups_manager() -> CgroupsManager:
    """Get global cgroups manager instance.

    Returns:
        Singleton cgroups manager
    """
    global _cgroups_manager
    if _cgroups_manager is None:
        _cgroups_manager = CgroupsManager()
    return _cgroups_manager
