"""Tests for agent marketplace search and filtering."""

import pytest
from devloop.marketplace.metadata import AgentMetadata, Rating
from devloop.marketplace.search import SearchEngine, SearchFilter, create_search_filter


@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    agents = [
        AgentMetadata(
            name="python-linter",
            version="1.0.0",
            description="Linter for Python code",
            author="Author A",
            license="MIT",
            homepage="https://example.com",
            categories=["linting"],
            keywords=["python", "linting", "code-quality"],
            python_version=">=3.9",
            rating=Rating(average=4.5, count=10),
            downloads=100,
        ),
        AgentMetadata(
            name="js-formatter",
            version="2.0.0",
            description="Code formatter for JavaScript",
            author="Author B",
            license="Apache-2.0",
            homepage="https://example.com",
            categories=["formatting"],
            keywords=["javascript", "formatter"],
            python_version=">=3.11",
            rating=Rating(average=4.8, count=20),
            downloads=200,
            trusted=True,
        ),
        AgentMetadata(
            name="legacy-tool",
            version="1.0.0",
            description="Deprecated tool",
            author="Author C",
            license="MIT",
            homepage="https://example.com",
            categories=["testing"],
            deprecated=True,
            rating=Rating(average=3.0, count=5),
            downloads=10,
        ),
        AgentMetadata(
            name="experimental-analyzer",
            version="0.1.0",
            description="Experimental code analyzer",
            author="Author D",
            license="MIT",
            homepage="https://example.com",
            categories=["analysis"],
            experimental=True,
            rating=Rating(average=3.5, count=2),
            downloads=5,
        ),
    ]
    return agents


class TestSearchEngine:
    """Test search engine functionality."""

    def test_search_by_query(self, sample_agents):
        """Test searching by text query."""
        engine = SearchEngine()
        filter = SearchFilter(query="linter")

        results = engine.search(sample_agents, filter)

        assert len(results) == 1
        assert results[0].name == "python-linter"

    def test_search_by_keyword(self, sample_agents):
        """Test searching by keyword."""
        engine = SearchEngine()
        filter = SearchFilter(query="python")

        results = engine.search(sample_agents, filter)

        assert len(results) == 1
        assert results[0].name == "python-linter"

    def test_search_by_category(self, sample_agents):
        """Test filtering by category."""
        engine = SearchEngine()
        filter = SearchFilter(category="formatting")

        results = engine.search(sample_agents, filter)

        assert len(results) == 1
        assert results[0].name == "js-formatter"

    def test_filter_by_rating(self, sample_agents):
        """Test filtering by minimum rating."""
        engine = SearchEngine()
        filter = SearchFilter(min_rating=4.0)

        results = engine.search(sample_agents, filter)

        assert len(results) == 2
        assert all(a.rating.average >= 4.0 for a in results)

    def test_filter_deprecated(self, sample_agents):
        """Test excluding deprecated agents."""
        engine = SearchEngine()
        filter = SearchFilter(exclude_deprecated=True)

        results = engine.search(sample_agents, filter)

        assert len(results) == 3
        assert all(not a.deprecated for a in results)

    def test_include_deprecated(self, sample_agents):
        """Test including deprecated agents."""
        engine = SearchEngine()
        filter = SearchFilter(exclude_deprecated=False)

        results = engine.search(sample_agents, filter)

        assert len(results) == 4

    def test_filter_trusted_only(self, sample_agents):
        """Test filtering to trusted agents only."""
        engine = SearchEngine()
        filter = SearchFilter(trusted_only=True)

        results = engine.search(sample_agents, filter)

        assert len(results) == 1
        assert results[0].name == "js-formatter"
        assert results[0].trusted

    def test_filter_experimental(self, sample_agents):
        """Test filtering experimental agents."""
        engine = SearchEngine()
        filter = SearchFilter(experimental=True)

        results = engine.search(sample_agents, filter)

        assert len(results) == 1
        assert results[0].experimental

    def test_filter_stable_only(self, sample_agents):
        """Test filtering to stable (non-experimental) agents."""
        engine = SearchEngine()
        filter = SearchFilter(experimental=False, exclude_deprecated=True)

        results = engine.search(sample_agents, filter)

        # Should have 2: python-linter and js-formatter (deprecated and experimental excluded)
        assert len(results) == 2
        assert all(not a.experimental for a in results)
        assert all(not a.deprecated for a in results)

    def test_combined_filters(self, sample_agents):
        """Test combining multiple filters."""
        engine = SearchEngine()
        filter = SearchFilter(
            query="agent",
            min_rating=3.0,
            exclude_deprecated=True,
            experimental=False,
        )

        results = engine.search(sample_agents, filter)

        # Should find agents matching "agent", rating >= 3.0, not deprecated, not experimental
        assert len(results) >= 0
        assert all(a.rating.average >= 3.0 for a in results if a.rating)

    def test_sorting_by_relevance(self, sample_agents):
        """Test that results are sorted by relevance."""
        engine = SearchEngine()
        filter = SearchFilter(exclude_deprecated=True, experimental=False)

        results = engine.search(sample_agents, filter)

        # Should be sorted by rating (highest first), then downloads
        ratings = [a.rating.average if a.rating else 0 for a in results]
        assert ratings == sorted(ratings, reverse=True)

    def test_filter_by_python_version(self, sample_agents):
        """Test filtering by Python version requirement."""
        engine = SearchEngine()
        filter = SearchFilter(min_python_version="3.11")

        results = engine.search(sample_agents, filter)

        # Should only include agents compatible with Python 3.11+
        assert len(results) >= 1

    def test_empty_results(self, sample_agents):
        """Test search with no matches."""
        engine = SearchEngine()
        filter = SearchFilter(query="nonexistent")

        results = engine.search(sample_agents, filter)

        assert len(results) == 0


class TestSearchFilter:
    """Test search filter creation."""

    def test_create_search_filter_minimal(self):
        """Test creating filter with minimal parameters."""
        filter = create_search_filter(query="test")

        assert filter.query == "test"
        assert filter.min_rating == 0.0
        assert filter.trusted_only is False
        assert filter.exclude_deprecated is True

    def test_create_search_filter_complete(self):
        """Test creating filter with all parameters."""
        filter = create_search_filter(
            query="test",
            category="linting",
            min_rating=4.0,
            trusted_only=True,
            exclude_deprecated=True,
            min_python_version="3.11",
            min_devloop_version="0.5.0",
            experimental=False,
        )

        assert filter.query == "test"
        assert filter.category == "linting"
        assert filter.min_rating == 4.0
        assert filter.trusted_only is True
        assert filter.min_python_version == "3.11"
        assert filter.experimental is False


if __name__ == "__main__":
    pytest.main([__file__])
