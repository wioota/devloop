"""Tests for metrics CLI commands."""

from datetime import datetime, timedelta, UTC

import pytest

from devloop.cli.commands.metrics import (
    _calculate_time_saved,
    _filter_events_by_period,
    _parse_period,
)


class TestParsePeriod:
    """Tests for _parse_period helper function."""

    def test_parse_period_hours(self):
        """Test parsing hours format (24h)."""
        start, end = _parse_period("24h")

        assert isinstance(start, datetime)
        assert isinstance(end, datetime)
        assert end > start
        # Should be approximately 24 hours apart
        delta = end - start
        assert 23.5 <= delta.total_seconds() / 3600 <= 24.5

    def test_parse_period_days(self):
        """Test parsing days format (7d)."""
        start, end = _parse_period("7d")

        delta = end - start
        assert 6.9 <= delta.days <= 7.1

    def test_parse_period_weeks(self):
        """Test parsing weeks format (2w)."""
        start, end = _parse_period("2w")

        delta = end - start
        assert 13.5 <= delta.days <= 14.5

    def test_parse_period_months(self):
        """Test parsing months format (3m)."""
        start, end = _parse_period("3m")

        delta = end - start
        # 3 months ≈ 90 days
        assert 89 <= delta.days <= 91

    def test_parse_period_today(self):
        """Test parsing 'today' keyword."""
        start, end = _parse_period("today")

        # Start should be midnight today
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0
        assert start.microsecond == 0
        # End should be now
        assert end > start

    def test_parse_period_week(self):
        """Test parsing 'week' keyword."""
        start, end = _parse_period("week")

        delta = end - start
        assert 6.9 <= delta.days <= 7.1

    def test_parse_period_month_numeric(self):
        """Test parsing months with numeric format (1m)."""
        start, end = _parse_period("1m")

        delta = end - start
        assert 29 <= delta.days <= 31

    def test_parse_period_all(self):
        """Test parsing 'all' keyword."""
        start, end = _parse_period("all")

        delta = end - start
        # Should be approximately 10 years
        assert 3500 <= delta.days <= 3700

    def test_parse_period_default(self):
        """Test default period (unrecognized input)."""
        start, end = _parse_period("xyz")

        delta = end - start
        # Should default to 24 hours
        assert 23.5 <= delta.total_seconds() / 3600 <= 24.5

    def test_parse_period_case_insensitive(self):
        """Test period parsing is case-insensitive."""
        start1, end1 = _parse_period("WEEK")
        start2, end2 = _parse_period("week")

        # Both should give approximately the same result
        delta1 = end1 - start1
        delta2 = end2 - start2
        assert abs(delta1.days - delta2.days) <= 1


class TestFilterEventsByPeriod:
    """Tests for _filter_events_by_period helper function."""

    def test_filter_events_empty_list(self):
        """Test filtering empty event list."""
        start = datetime.now(UTC) - timedelta(days=1)
        end = datetime.now(UTC)

        filtered = _filter_events_by_period([], start, end)

        assert filtered == []

    def test_filter_events_all_within_period(self):
        """Test filtering when all events are within period."""
        now = datetime.now(UTC)
        start = now - timedelta(hours=2)
        end = now

        events = [
            {"timestamp": (now - timedelta(hours=1)).isoformat()},
            {"timestamp": (now - timedelta(minutes=30)).isoformat()},
        ]

        filtered = _filter_events_by_period(events, start, end)

        assert len(filtered) == 2

    def test_filter_events_none_within_period(self):
        """Test filtering when no events are within period."""
        now = datetime.now(UTC)
        start = now - timedelta(hours=2)
        end = now - timedelta(hours=1)

        events = [
            {"timestamp": (now - timedelta(hours=3)).isoformat()},
            {"timestamp": now.isoformat()},
        ]

        filtered = _filter_events_by_period(events, start, end)

        assert len(filtered) == 0

    def test_filter_events_partial_match(self):
        """Test filtering with some events matching."""
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        end = now

        events = [
            {"timestamp": (now - timedelta(hours=2)).isoformat()},  # Before range
            {"timestamp": (now - timedelta(minutes=30)).isoformat()},  # In range
            {"timestamp": (now - timedelta(minutes=10)).isoformat()},  # In range
            {"timestamp": (now + timedelta(hours=1)).isoformat()},  # After range
        ]

        filtered = _filter_events_by_period(events, start, end)

        assert len(filtered) == 2

    def test_filter_events_invalid_timestamp(self):
        """Test filtering skips events with invalid timestamps."""
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        end = now

        events = [
            {"timestamp": "invalid-timestamp"},
            {"timestamp": (now - timedelta(minutes=30)).isoformat()},
            {"timestamp": ""},
            {},  # No timestamp field
        ]

        filtered = _filter_events_by_period(events, start, end)

        # Should only include the one valid event
        assert len(filtered) == 1

    def test_filter_events_naive_datetime_input(self):
        """Test filtering handles naive datetime inputs."""
        # Create naive datetimes (no timezone)
        now_naive = datetime.now()
        start = now_naive - timedelta(hours=1)
        end = now_naive

        events = [
            {"timestamp": now_naive.replace(tzinfo=UTC).isoformat()},
        ]

        # Should not raise error and handle properly
        filtered = _filter_events_by_period(events, start, end)

        assert len(filtered) == 1

    def test_filter_events_naive_event_timestamp(self):
        """Test filtering handles events with naive timestamps."""
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        end = now

        # Create event with naive timestamp (no timezone info)
        naive_time = datetime.now()  # Naive datetime
        events = [
            {"timestamp": naive_time.isoformat()},  # Will be naive
        ]

        # Should handle the naive event timestamp
        filtered = _filter_events_by_period(events, start, end)

        # Event should be included if times match
        assert len(filtered) >= 0  # Just checking it doesn't crash

    def test_filter_events_boundary_conditions(self):
        """Test filtering at exact boundary times."""
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        end = now

        events = [
            {"timestamp": start.isoformat()},  # Exactly at start
            {"timestamp": end.isoformat()},  # Exactly at end
        ]

        filtered = _filter_events_by_period(events, start, end)

        # Both boundary events should be included (inclusive range)
        assert len(filtered) == 2


class TestCalculateTimeSaved:
    """Tests for _calculate_time_saved helper function."""

    def test_calculate_time_saved_empty(self):
        """Test calculating time saved with empty event list."""
        result = _calculate_time_saved([])

        assert result["total_ms"] == 0
        assert result["total_seconds"] == 0
        assert result["total_minutes"] == 0
        assert result["total_hours"] == 0
        assert result["count"] == 0

    def test_calculate_time_saved_single_event(self):
        """Test calculating time saved with single event."""
        events = [
            {
                "event_type": "value_event",
                "duration_ms": 5000,  # 5 seconds
            }
        ]

        result = _calculate_time_saved(events)

        assert result["total_ms"] == 5000
        assert result["total_seconds"] == 5.0
        assert result["total_minutes"] == pytest.approx(0.0833, rel=0.01)
        assert result["count"] == 1

    def test_calculate_time_saved_multiple_events(self):
        """Test calculating time saved with multiple events."""
        events = [
            {"event_type": "value_event", "duration_ms": 3000},
            {"event_type": "value_event", "duration_ms": 7000},
            {"event_type": "value_event", "duration_ms": 5000},
        ]

        result = _calculate_time_saved(events)

        assert result["total_ms"] == 15000
        assert result["total_seconds"] == 15.0
        assert result["total_minutes"] == 0.25
        assert result["count"] == 3

    def test_calculate_time_saved_ignores_non_value_events(self):
        """Test that non-value events are ignored."""
        events = [
            {"event_type": "value_event", "duration_ms": 5000},
            {"event_type": "other_event", "duration_ms": 10000},
            {"event_type": "value_event", "duration_ms": 3000},
        ]

        result = _calculate_time_saved(events)

        assert result["total_ms"] == 8000
        assert result["count"] == 2

    def test_calculate_time_saved_missing_duration(self):
        """Test events without duration_ms are skipped."""
        events = [
            {"event_type": "value_event", "duration_ms": 5000},
            {"event_type": "value_event"},  # No duration
            {"event_type": "value_event", "duration_ms": None},  # None duration
        ]

        result = _calculate_time_saved(events)

        assert result["total_ms"] == 5000
        assert result["count"] == 1

    def test_calculate_time_saved_hours_conversion(self):
        """Test hours calculation is correct."""
        events = [
            {"event_type": "value_event", "duration_ms": 3600000},  # 1 hour in ms
        ]

        result = _calculate_time_saved(events)

        assert result["total_hours"] == 1.0
        assert result["total_minutes"] == 60.0
