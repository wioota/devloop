"""Tests for OpenTelemetry-based telemetry management."""

import json
import tempfile
from pathlib import Path

import pytest

from devloop.telemetry.telemetry_manager import TelemetryManager, get_telemetry_manager


class TestTelemetryManager:
    """Tests for TelemetryManager."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_telemetry_manager_initialization(self, temp_config_dir):
        """Test TelemetryManager can be initialized."""
        manager = TelemetryManager(config_dir=temp_config_dir)
        assert manager is not None
        assert manager.backend == "local"

    def test_telemetry_manager_local_backend(self, temp_config_dir):
        """Test local backend setup."""
        manager = TelemetryManager(backend="local", config_dir=temp_config_dir)
        assert manager.backend == "local"
        assert hasattr(manager, "traces_file")
        assert hasattr(manager, "metrics_file")

    def test_record_trace(self, temp_config_dir):
        """Test recording a trace."""
        manager = TelemetryManager(config_dir=temp_config_dir)
        manager.record_trace(
            "test_span",
            attributes={"key": "value"},
            duration_ms=100,
            status="OK",
        )

        traces = manager.get_traces()
        assert len(traces) == 1
        assert traces[0]["span_name"] == "test_span"
        assert traces[0]["status"] == "OK"
        assert traces[0]["duration_ms"] == 100
        assert traces[0]["attributes"]["key"] == "value"

    def test_record_metric(self, temp_config_dir):
        """Test recording a metric."""
        manager = TelemetryManager(config_dir=temp_config_dir)
        manager.record_metric("test_metric", 42.5, attributes={"unit": "ms"})

        metrics = manager.get_metrics()
        assert len(metrics) == 1
        assert metrics[0]["metric_name"] == "test_metric"
        assert metrics[0]["value"] == 42.5
        assert metrics[0]["attributes"]["unit"] == "ms"

    def test_multiple_traces(self, temp_config_dir):
        """Test recording multiple traces."""
        manager = TelemetryManager(config_dir=temp_config_dir)

        for i in range(5):
            manager.record_trace(f"span_{i}", duration_ms=i * 10)

        traces = manager.get_traces()
        assert len(traces) == 5
        assert traces[0]["span_name"] == "span_0"
        assert traces[-1]["span_name"] == "span_4"

    def test_multiple_metrics(self, temp_config_dir):
        """Test recording multiple metrics."""
        manager = TelemetryManager(config_dir=temp_config_dir)

        for i in range(5):
            manager.record_metric(f"metric_{i}", float(i))

        metrics = manager.get_metrics()
        assert len(metrics) == 5
        assert metrics[0]["metric_name"] == "metric_0"
        assert metrics[-1]["metric_name"] == "metric_4"

    def test_traces_disabled(self, temp_config_dir):
        """Test that tracing can be disabled."""
        manager = TelemetryManager(
            config_dir=temp_config_dir, enable_traces=False
        )
        manager.record_trace("test_span")

        traces = manager.get_traces()
        assert len(traces) == 0

    def test_metrics_disabled(self, temp_config_dir):
        """Test that metrics can be disabled."""
        manager = TelemetryManager(
            config_dir=temp_config_dir, enable_metrics=False
        )
        manager.record_metric("test_metric", 42.0)

        metrics = manager.get_metrics()
        assert len(metrics) == 0

    def test_clear_local_data(self, temp_config_dir):
        """Test clearing local telemetry data."""
        manager = TelemetryManager(config_dir=temp_config_dir)

        # Add some data
        manager.record_trace("test_span")
        manager.record_metric("test_metric", 42.0)

        # Verify data exists
        assert len(manager.get_traces()) > 0
        assert len(manager.get_metrics()) > 0

        # Clear data
        manager.clear_local_data()

        # Verify data is cleared
        assert len(manager.get_traces()) == 0
        assert len(manager.get_metrics()) == 0

    def test_export_summary(self, temp_config_dir):
        """Test exporting telemetry summary."""
        manager = TelemetryManager(config_dir=temp_config_dir)

        # Add some data
        manager.record_trace("test_span")
        manager.record_metric("test_metric", 42.0)

        summary = manager.export_summary()
        assert summary["backend"] == "local"
        assert summary["traces_count"] >= 1
        assert summary["metrics_count"] >= 1
        assert summary["traces_enabled"] is True
        assert summary["metrics_enabled"] is True

    def test_trace_limit(self, temp_config_dir):
        """Test trace retrieval limit."""
        manager = TelemetryManager(config_dir=temp_config_dir)

        # Add 20 traces
        for i in range(20):
            manager.record_trace(f"span_{i}")

        # Get only 5
        traces = manager.get_traces(limit=5)
        assert len(traces) == 5
        # Should be the last 5
        assert traces[0]["span_name"] == "span_15"
        assert traces[-1]["span_name"] == "span_19"

    def test_metric_limit(self, temp_config_dir):
        """Test metric retrieval limit."""
        manager = TelemetryManager(config_dir=temp_config_dir)

        # Add 20 metrics
        for i in range(20):
            manager.record_metric(f"metric_{i}", float(i))

        # Get only 5
        metrics = manager.get_metrics(limit=5)
        assert len(metrics) == 5
        # Should be the last 5
        assert metrics[0]["metric_name"] == "metric_15"
        assert metrics[-1]["metric_name"] == "metric_19"

    def test_global_telemetry_manager(self, temp_config_dir):
        """Test global telemetry manager singleton."""
        manager1 = get_telemetry_manager(config_dir=temp_config_dir)
        manager2 = get_telemetry_manager(config_dir=temp_config_dir)

        # Should be the same instance
        assert manager1 is manager2

    def test_jaeger_backend_initialization(self):
        """Test Jaeger backend initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TelemetryManager(backend="jaeger", config_dir=tmpdir)
            assert manager.backend == "jaeger"
            assert hasattr(manager, "jaeger_endpoint")

    def test_prometheus_backend_initialization(self):
        """Test Prometheus backend initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TelemetryManager(backend="prometheus", config_dir=tmpdir)
            assert manager.backend == "prometheus"
            assert hasattr(manager, "prometheus_port")

    def test_otlp_backend_initialization(self):
        """Test OTLP backend initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TelemetryManager(backend="otlp", config_dir=tmpdir)
            assert manager.backend == "otlp"
            assert hasattr(manager, "otlp_endpoint")

    def test_unknown_backend_fallback(self):
        """Test fallback to local backend for unknown backends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TelemetryManager(backend="unknown", config_dir=tmpdir)
            # Should fall back to local
            assert manager.backend == "unknown"  # Still reports requested backend
            assert hasattr(manager, "traces_file")  # But has local files

    def test_trace_with_no_attributes(self, temp_config_dir):
        """Test recording trace without attributes."""
        manager = TelemetryManager(config_dir=temp_config_dir)
        manager.record_trace("test_span", duration_ms=50)

        traces = manager.get_traces()
        assert len(traces) == 1
        assert traces[0]["attributes"] == {}

    def test_metric_with_custom_unit(self, temp_config_dir):
        """Test recording metric with custom unit."""
        manager = TelemetryManager(config_dir=temp_config_dir)
        manager.record_metric("response_time", 125.5, unit="ms")

        metrics = manager.get_metrics()
        assert len(metrics) == 1
        assert metrics[0]["unit"] == "ms"
        assert metrics[0]["value"] == 125.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
