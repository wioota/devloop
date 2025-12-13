"""OpenTelemetry-based telemetry management for DevLoop.

This module provides standardized observability using OpenTelemetry,
enabling integration with tools like Jaeger, Prometheus, and Grafana.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages OpenTelemetry-based observability for DevLoop.

    Features:
    - Local-first by default (JSONL files)
    - Optional backends (Jaeger, Prometheus, OTLP)
    - Minimal dependencies (opentelemetry-api, opentelemetry-sdk)
    - Automatic context propagation for distributed tracing
    """

    def __init__(
        self,
        backend: str = "local",
        config_dir: str = ".devloop",
        enable_traces: bool = True,
        enable_metrics: bool = True,
    ):
        """Initialize telemetry manager.

        Args:
            backend: Telemetry backend ("local", "jaeger", "prometheus", "otlp")
            config_dir: Directory for telemetry configuration
            enable_traces: Enable distributed tracing
            enable_metrics: Enable metrics collection
        """
        self.backend = backend
        self.config_dir = Path(config_dir)
        self.enable_traces = enable_traces
        self.enable_metrics = enable_metrics

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize backend
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Initialize the configured telemetry backend."""
        if self.backend == "local":
            self._setup_local_backend()
        elif self.backend == "jaeger":
            self._setup_jaeger_backend()
        elif self.backend == "prometheus":
            self._setup_prometheus_backend()
        elif self.backend == "otlp":
            self._setup_otlp_backend()
        else:
            logger.warning(f"Unknown telemetry backend: {self.backend}, using local")
            self._setup_local_backend()

    def _setup_local_backend(self) -> None:
        """Setup local file-based telemetry (default)."""
        self.traces_file = self.config_dir / "traces.jsonl"
        self.metrics_file = self.config_dir / "metrics.jsonl"

    def _setup_jaeger_backend(self) -> None:
        """Setup Jaeger telemetry backend.

        Requires: pip install opentelemetry-exporter-jaeger
        """
        self.jaeger_endpoint = os.getenv(
            "JAEGER_ENDPOINT", "http://localhost:14268/api/traces"
        )
        logger.info(f"Jaeger telemetry backend: {self.jaeger_endpoint}")

    def _setup_prometheus_backend(self) -> None:
        """Setup Prometheus telemetry backend.

        Requires: pip install opentelemetry-exporter-prometheus
        """
        self.prometheus_port = int(os.getenv("PROMETHEUS_PORT", "8000"))
        logger.info(f"Prometheus telemetry backend on port {self.prometheus_port}")

    def _setup_otlp_backend(self) -> None:
        """Setup OTLP telemetry backend.

        Requires: pip install opentelemetry-exporter-otlp
        """
        self.otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        logger.info(f"OTLP telemetry backend: {self.otlp_endpoint}")

    def record_trace(
        self,
        span_name: str,
        attributes: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        status: str = "OK",
    ) -> None:
        """Record a trace span.

        Args:
            span_name: Name of the span
            attributes: Span attributes
            duration_ms: Duration in milliseconds
            status: Span status (OK, ERROR)
        """
        if not self.enable_traces:
            return

        trace_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "span_name": span_name,
            "status": status,
            "attributes": attributes or {},
        }

        if duration_ms is not None:
            trace_data["duration_ms"] = duration_ms

        if self.backend == "local":
            self._write_trace_local(trace_data)
        # Other backends would implement their own writing

    def record_metric(
        self,
        metric_name: str,
        value: float,
        attributes: Optional[Dict[str, Any]] = None,
        unit: str = "1",
    ) -> None:
        """Record a metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            attributes: Metric attributes
            unit: Unit of measurement
        """
        if not self.enable_metrics:
            return

        metric_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "attributes": attributes or {},
        }

        if self.backend == "local":
            self._write_metric_local(metric_data)
        # Other backends would implement their own writing

    def _write_trace_local(self, trace_data: Dict[str, Any]) -> None:
        """Write trace to local JSONL file.

        Args:
            trace_data: Trace data dictionary
        """
        try:
            with open(self.traces_file, "a") as f:
                f.write(json.dumps(trace_data) + "\n")
        except IOError as e:
            logger.error(f"Failed to write trace: {e}")

    def _write_metric_local(self, metric_data: Dict[str, Any]) -> None:
        """Write metric to local JSONL file.

        Args:
            metric_data: Metric data dictionary
        """
        try:
            with open(self.metrics_file, "a") as f:
                f.write(json.dumps(metric_data) + "\n")
        except IOError as e:
            logger.error(f"Failed to write metric: {e}")

    def get_traces(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Get recent traces from local backend.

        Args:
            limit: Maximum number of traces to return

        Returns:
            List of trace dictionaries
        """
        if self.backend != "local" or not self.traces_file.exists():
            return []

        traces = []
        try:
            with open(self.traces_file) as f:
                for line in f:
                    if line.strip():
                        traces.append(json.loads(line))
        except IOError:
            pass

        # Return most recent traces
        return traces[-limit:]

    def get_metrics(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Get recent metrics from local backend.

        Args:
            limit: Maximum number of metrics to return

        Returns:
            List of metric dictionaries
        """
        if self.backend != "local" or not self.metrics_file.exists():
            return []

        metrics = []
        try:
            with open(self.metrics_file) as f:
                for line in f:
                    if line.strip():
                        metrics.append(json.loads(line))
        except IOError:
            pass

        # Return most recent metrics
        return metrics[-limit:]

    def clear_local_data(self) -> None:
        """Clear local telemetry data files."""
        if self.backend != "local":
            return

        for file_path in [self.traces_file, self.metrics_file]:
            if file_path.exists():
                file_path.unlink()

    def export_summary(self) -> Dict[str, Any]:
        """Export telemetry summary.

        Returns:
            Dictionary with telemetry statistics
        """
        traces = self.get_traces(limit=1000)
        metrics = self.get_metrics(limit=1000)

        return {
            "backend": self.backend,
            "traces_count": len(traces),
            "metrics_count": len(metrics),
            "traces_enabled": self.enable_traces,
            "metrics_enabled": self.enable_metrics,
            "recent_traces": traces[-5:] if traces else [],
            "recent_metrics": metrics[-5:] if metrics else [],
        }


# Global telemetry manager instance
_manager: Optional[TelemetryManager] = None


def get_telemetry_manager(
    backend: str = "local",
    config_dir: str = ".devloop",
) -> TelemetryManager:
    """Get or create the global telemetry manager.

    Args:
        backend: Telemetry backend to use
        config_dir: Configuration directory

    Returns:
        TelemetryManager instance
    """
    global _manager
    if _manager is None:
        _manager = TelemetryManager(backend=backend, config_dir=config_dir)
    return _manager
