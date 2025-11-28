"""Performance monitoring and resource usage analytics."""

from __future__ import annotations

import asyncio
import json
import psutil
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles


@dataclass
class ResourceUsage:
    """Resource usage snapshot."""

    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0

    @classmethod
    def snapshot(cls) -> ResourceUsage:
        """Create a resource usage snapshot."""
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.1)

        # Get system-wide I/O counters (since process I/O counters might not be available)
        try:
            io_counters = psutil.disk_io_counters()
            disk_read_mb = (
                io_counters.read_bytes / (1024 * 1024) if io_counters else 0.0
            )
            disk_write_mb = (
                io_counters.write_bytes / (1024 * 1024) if io_counters else 0.0
            )
        except (AttributeError, psutil.AccessDenied):
            disk_read_mb = 0.0
            disk_write_mb = 0.0

        # Get network I/O
        try:
            net_counters = psutil.net_io_counters()
            network_bytes_sent = net_counters.bytes_sent if net_counters else 0
            network_bytes_recv = net_counters.bytes_recv if net_counters else 0
        except (AttributeError, psutil.AccessDenied):
            network_bytes_sent = 0
            network_bytes_recv = 0

        return cls(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_mb=memory_info.rss / (1024 * 1024),  # Convert to MB
            memory_percent=process.memory_percent(),
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
        )


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation."""

    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    resource_usage_start: Optional[ResourceUsage] = None
    resource_usage_end: Optional[ResourceUsage] = None
    cpu_used: Optional[float] = None
    memory_used_mb: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def complete(self, success: bool, error_message: Optional[str] = None) -> None:
        """Mark the operation as complete."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message

        if self.resource_usage_start and self.resource_usage_end:
            self.cpu_used = (
                self.resource_usage_end.cpu_percent
                - self.resource_usage_start.cpu_percent
            )
            self.memory_used_mb = (
                self.resource_usage_end.memory_mb - self.resource_usage_start.memory_mb
            )


class PerformanceMonitor:
    """Monitor performance and resource usage."""

    def __init__(self, storage_path: Path, retention_days: int = 30):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.metrics_file = storage_path / "metrics.jsonl"
        self.retention_days = retention_days

    @asynccontextmanager
    async def monitor_operation(
        self, operation_name: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Context manager to monitor an operation."""
        start_usage = ResourceUsage.snapshot()
        start_time = time.time()

        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=start_time,
            resource_usage_start=start_usage,
            metadata=metadata or {},
        )

        try:
            yield metrics
            end_usage = ResourceUsage.snapshot()
            metrics.resource_usage_end = end_usage
            metrics.complete(success=True)

        except Exception as e:
            end_usage = ResourceUsage.snapshot()
            metrics.resource_usage_end = end_usage
            metrics.complete(success=False, error_message=str(e))
            raise

        finally:
            await self._store_metrics(metrics)

    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics."""
        usage = ResourceUsage.snapshot()

        # Get system-wide metrics
        system_cpu = psutil.cpu_percent(interval=0.1)
        system_memory = psutil.virtual_memory()
        system_disk = psutil.disk_usage("/")

        return {
            "timestamp": usage.timestamp,
            "process": {
                "cpu_percent": usage.cpu_percent,
                "memory_mb": usage.memory_mb,
                "memory_percent": usage.memory_percent,
            },
            "system": {
                "cpu_percent": system_cpu,
                "memory_percent": system_memory.percent,
                "memory_used_gb": system_memory.used / (1024**3),
                "memory_total_gb": system_memory.total / (1024**3),
                "disk_percent": system_disk.percent,
                "disk_used_gb": system_disk.used / (1024**3),
                "disk_total_gb": system_disk.total / (1024**3),
            },
        }

    async def get_performance_summary(
        self, operation_name: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """Get performance summary for operations."""
        cutoff_time = time.time() - (hours * 3600)

        operations = await self._load_recent_metrics(cutoff_time)
        if operation_name:
            operations = [
                op for op in operations if op.operation_name == operation_name
            ]

        if not operations:
            return {
                "operation_name": operation_name or "all",
                "time_range_hours": hours,
                "total_operations": 0,
                "success_rate": 0.0,
                "average_duration": 0.0,
                "average_cpu_usage": 0.0,
                "average_memory_usage_mb": 0.0,
            }

        successful_ops = [op for op in operations if op.success]
        success_rate = len(successful_ops) / len(operations) * 100

        durations = [op.duration for op in operations if op.duration is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        cpu_usages = [op.cpu_used for op in operations if op.cpu_used is not None]
        avg_cpu = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0.0

        memory_usages = [
            op.memory_used_mb for op in operations if op.memory_used_mb is not None
        ]
        avg_memory = sum(memory_usages) / len(memory_usages) if memory_usages else 0.0

        return {
            "operation_name": operation_name or "all",
            "time_range_hours": hours,
            "total_operations": len(operations),
            "success_rate": round(success_rate, 1),
            "average_duration": round(avg_duration, 2),
            "average_cpu_usage": round(avg_cpu, 1),
            "average_memory_usage_mb": round(avg_memory, 2),
        }

    async def get_resource_trends(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get resource usage trends over time."""
        cutoff_time = time.time() - (hours * 3600)
        operations = await self._load_recent_metrics(cutoff_time)

        # Group by hour
        hourly_data = {}
        for op in operations:
            if op.resource_usage_start:
                hour = int(op.start_time // 3600)
                if hour not in hourly_data:
                    hourly_data[hour] = {
                        "hour": hour,
                        "timestamp": hour * 3600,
                        "operations": 0,
                        "avg_cpu": 0.0,
                        "avg_memory_mb": 0.0,
                        "cpu_samples": [],
                        "memory_samples": [],
                    }

                hourly_data[hour]["operations"] += 1
                if op.cpu_used is not None:
                    hourly_data[hour]["cpu_samples"].append(op.cpu_used)
                if op.memory_used_mb is not None:
                    hourly_data[hour]["memory_samples"].append(op.memory_used_mb)

        # Calculate averages
        trends = []
        for hour_data in hourly_data.values():
            if hour_data["cpu_samples"]:
                hour_data["avg_cpu"] = sum(hour_data["cpu_samples"]) / len(
                    hour_data["cpu_samples"]
                )
            if hour_data["memory_samples"]:
                hour_data["avg_memory_mb"] = sum(hour_data["memory_samples"]) / len(
                    hour_data["memory_samples"]
                )

            del hour_data["cpu_samples"]
            del hour_data["memory_samples"]
            trends.append(hour_data)

        return sorted(trends, key=lambda x: x["timestamp"])

    async def _store_metrics(self, metrics: PerformanceMetrics) -> None:
        """Store performance metrics."""
        metrics_dict = {
            "operation_name": metrics.operation_name,
            "start_time": metrics.start_time,
            "end_time": metrics.end_time,
            "duration": metrics.duration,
            "success": metrics.success,
            "error_message": metrics.error_message,
            "metadata": metrics.metadata,
        }

        if metrics.resource_usage_start:
            metrics_dict["resource_usage_start"] = {
                "timestamp": metrics.resource_usage_start.timestamp,
                "cpu_percent": metrics.resource_usage_start.cpu_percent,
                "memory_mb": metrics.resource_usage_start.memory_mb,
                "memory_percent": metrics.resource_usage_start.memory_percent,
                "disk_read_mb": metrics.resource_usage_start.disk_read_mb,
                "disk_write_mb": metrics.resource_usage_start.disk_write_mb,
                "network_bytes_sent": metrics.resource_usage_start.network_bytes_sent,
                "network_bytes_recv": metrics.resource_usage_start.network_bytes_recv,
            }

        if metrics.resource_usage_end:
            metrics_dict["resource_usage_end"] = {
                "timestamp": metrics.resource_usage_end.timestamp,
                "cpu_percent": metrics.resource_usage_end.cpu_percent,
                "memory_mb": metrics.resource_usage_end.memory_mb,
                "memory_percent": metrics.resource_usage_end.memory_percent,
                "disk_read_mb": metrics.resource_usage_end.disk_read_mb,
                "disk_write_mb": metrics.resource_usage_end.disk_write_mb,
                "network_bytes_sent": metrics.resource_usage_end.network_bytes_sent,
                "network_bytes_recv": metrics.resource_usage_end.network_bytes_recv,
            }

        if metrics.cpu_used is not None:
            metrics_dict["cpu_used"] = metrics.cpu_used
        if metrics.memory_used_mb is not None:
            metrics_dict["memory_used_mb"] = metrics.memory_used_mb

        async with aiofiles.open(self.metrics_file, "a") as f:
            await f.write(json.dumps(metrics_dict) + "\n")

        # Cleanup old metrics
        await self._cleanup_old_metrics()

    async def _load_recent_metrics(
        self, cutoff_time: float
    ) -> List[PerformanceMetrics]:
        """Load metrics newer than cutoff time."""
        metrics = []

        if not self.metrics_file.exists():
            return metrics

        async with aiofiles.open(self.metrics_file, "r") as f:
            lines = await f.readlines()

        for line in lines:
            try:
                data = json.loads(line.strip())
                if data["start_time"] >= cutoff_time:
                    start_usage = None
                    end_usage = None

                    if "resource_usage_start" in data:
                        start_usage = ResourceUsage(**data["resource_usage_start"])

                    if "resource_usage_end" in data:
                        end_usage = ResourceUsage(**data["resource_usage_end"])

                    metrics.append(
                        PerformanceMetrics(
                            operation_name=data["operation_name"],
                            start_time=data["start_time"],
                            end_time=data.get("end_time"),
                            duration=data.get("duration"),
                            resource_usage_start=start_usage,
                            resource_usage_end=end_usage,
                            cpu_used=data.get("cpu_used"),
                            memory_used_mb=data.get("memory_used_mb"),
                            success=data.get("success"),
                            error_message=data.get("error_message"),
                            metadata=data.get("metadata", {}),
                        )
                    )
            except (json.JSONDecodeError, KeyError):
                continue

        return metrics

    async def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff_time = time.time() - (self.retention_days * 24 * 3600)

        if not self.metrics_file.exists():
            return

        # Read all metrics
        async with aiofiles.open(self.metrics_file, "r") as f:
            lines = await f.readlines()

        # Filter recent metrics
        recent_lines = []
        for line in lines:
            try:
                data = json.loads(line.strip())
                if data["start_time"] >= cutoff_time:
                    recent_lines.append(line)
            except (json.JSONDecodeError, KeyError):
                continue

        # Write back recent metrics
        async with aiofiles.open(self.metrics_file, "w") as f:
            await f.writelines(recent_lines)


class PerformanceOptimizer:
    """Optimize performance based on monitoring data."""

    def __init__(self, performance_monitor: PerformanceMonitor):
        self.monitor = performance_monitor
        self._debounce_cache: Dict[str, float] = {}
        self._concurrency_limits: Dict[str, asyncio.Semaphore] = {}

    async def should_skip_operation(
        self, operation_key: str, debounce_seconds: float = 1.0
    ) -> bool:
        """Check if operation should be debounced."""
        now = time.time()
        last_run = self._debounce_cache.get(operation_key, 0)

        if now - last_run < debounce_seconds:
            return True

        self._debounce_cache[operation_key] = now
        return False

    def get_concurrency_limiter(
        self, operation_type: str, max_concurrent: int
    ) -> asyncio.Semaphore:
        """Get a semaphore for limiting concurrency."""
        if operation_type not in self._concurrency_limits:
            self._concurrency_limits[operation_type] = asyncio.Semaphore(max_concurrent)
        return self._concurrency_limits[operation_type]

    async def get_optimal_config(self, operation_name: str) -> Dict[str, Any]:
        """Get optimal configuration based on performance history."""
        summary = await self.monitor.get_performance_summary(operation_name, hours=24)

        # Simple optimization logic based on performance data
        config = {}

        if summary["total_operations"] > 10:  # Need some data
            # If average duration is high, suggest debouncing
            if summary["average_duration"] > 2.0:
                config["debounce_seconds"] = min(summary["average_duration"] * 0.5, 5.0)

            # If CPU usage is high, suggest lower concurrency
            if summary["average_cpu_usage"] > 50:
                config["max_concurrent"] = max(
                    1, int(10 / (summary["average_cpu_usage"] / 10))
                )

            # If memory usage is high, suggest smaller batches
            if summary["average_memory_usage_mb"] > 100:
                config["batch_size"] = max(
                    1, int(100 / summary["average_memory_usage_mb"] * 10)
                )

        return config
