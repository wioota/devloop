"""Tests for agent marketplace metadata."""

import json
import pytest
from pathlib import Path

from devloop.marketplace.metadata import (
    AgentMetadata,
    Dependency,
    Rating,
)


class TestDependency:
    """Test dependency specification."""

    def test_dependency_creation(self):
        """Test creating a dependency."""
        dep = Dependency(
            name="requests",
            version=">=2.28.0",
            optional=False,
            description="HTTP library",
        )

        assert dep.name == "requests"
        assert dep.version == ">=2.28.0"
        assert not dep.optional
        assert dep.description == "HTTP library"

    def test_dependency_to_dict(self):
        """Test dependency serialization."""
        dep = Dependency(
            name="requests",
            version=">=2.28.0",
            optional=True,
        )

        data = dep.to_dict()
        assert data["name"] == "requests"
        assert data["version"] == ">=2.28.0"
        assert data["optional"] is True


class TestRating:
    """Test agent rating."""

    def test_rating_creation(self):
        """Test creating a rating."""
        rating = Rating(average=4.5, count=10)

        assert rating.average == 4.5
        assert rating.count == 10
        assert rating.distribution == {}

    def test_rating_with_distribution(self):
        """Test rating with star distribution."""
        rating = Rating(
            average=4.2,
            count=5,
            distribution={5: 3, 4: 1, 3: 1},
        )

        assert rating.average == 4.2
        assert rating.count == 5
        assert rating.distribution[5] == 3


class TestAgentMetadata:
    """Test agent metadata."""

    def test_minimal_metadata(self):
        """Test creating metadata with required fields only."""
        metadata = AgentMetadata(
            name="my-linter",
            version="1.0.0",
            description="A custom linter",
            author="John Doe",
            license="MIT",
            homepage="https://example.com",
        )

        assert metadata.name == "my-linter"
        assert metadata.version == "1.0.0"
        assert metadata.description == "A custom linter"
        assert metadata.author == "John Doe"
        assert metadata.license == "MIT"

    def test_complete_metadata(self):
        """Test creating metadata with all fields."""
        dep = Dependency(name="requests", version=">=2.28.0")
        rating = Rating(average=4.5, count=10)

        metadata = AgentMetadata(
            name="my-formatter",
            version="2.1.0",
            description="Custom code formatter",
            author="Jane Smith",
            license="Apache-2.0",
            homepage="https://example.com",
            repository="https://github.com/jane/formatter",
            documentation="https://formatter.docs.io",
            keywords=["formatting", "code-style"],
            categories=["formatting"],
            python_version=">=3.9",
            devloop_version=">=0.4.0",
            dependencies=[dep],
            published_at="2025-01-01T00:00:00",
            updated_at="2025-01-15T12:00:00",
            downloads=500,
            rating=rating,
            trusted=True,
        )

        assert metadata.name == "my-formatter"
        assert metadata.trusted is True
        assert len(metadata.dependencies) == 1
        assert metadata.rating.average == 4.5

    def test_validate_required_fields(self):
        """Test validation of required fields."""
        metadata = AgentMetadata(
            name="",
            version="1.0.0",
            description="Test",
            author="Test",
            license="MIT",
        )

        errors = metadata.validate()
        assert any("name is required" in e for e in errors)

    def test_validate_description_length(self):
        """Test validation of description length."""
        long_desc = "x" * 501
        metadata = AgentMetadata(
            name="test",
            version="1.0.0",
            description=long_desc,
            author="Test",
            license="MIT",
            homepage="https://example.com",
        )

        errors = metadata.validate()
        assert any("description must be <= 500 characters" in e for e in errors)

    def test_validate_name_format(self):
        """Test validation of agent name format."""
        invalid_names = [
            "my agent",  # spaces
            "my@agent",  # special chars
            "my.agent",  # dots
        ]

        for invalid_name in invalid_names:
            metadata = AgentMetadata(
                name=invalid_name,
                version="1.0.0",
                description="Test",
                author="Test",
                license="MIT",
                homepage="https://example.com",
            )

            errors = metadata.validate()
            assert any("name must contain only alphanumeric" in e for e in errors)

    def test_validate_valid_names(self):
        """Test that valid names pass validation."""
        valid_names = [
            "my-agent",
            "my_agent",
            "MyAgent",
            "my-agent-123",
        ]

        for valid_name in valid_names:
            metadata = AgentMetadata(
                name=valid_name,
                version="1.0.0",
                description="Test",
                author="Test",
                license="MIT",
                homepage="https://example.com",
            )

            errors = [e for e in metadata.validate() if "name must contain" in e]
            assert len(errors) == 0

    def test_validate_version_format(self):
        """Test validation of semantic versioning."""
        invalid_versions = ["1", "1.0", "1.0.0.0", "v1.0.0"]

        for invalid_version in invalid_versions:
            metadata = AgentMetadata(
                name="test",
                version=invalid_version,
                description="Test",
                author="Test",
                license="MIT",
                homepage="https://example.com",
            )

            errors = metadata.validate()
            assert any("version must be valid" in e for e in errors)

    def test_validate_homepage_or_repository(self):
        """Test that either homepage or repository is required."""
        metadata = AgentMetadata(
            name="test",
            version="1.0.0",
            description="Test",
            author="Test",
            license="MIT",
        )

        errors = metadata.validate()
        assert any("either homepage or repository is required" in e for e in errors)

    def test_metadata_to_dict(self):
        """Test metadata serialization to dictionary."""
        metadata = AgentMetadata(
            name="test-agent",
            version="1.0.0",
            description="Test",
            author="Test",
            license="MIT",
            homepage="https://example.com",
            keywords=["test"],
        )

        data = metadata.to_dict()

        assert data["name"] == "test-agent"
        assert data["version"] == "1.0.0"
        assert data["keywords"] == ["test"]

    def test_metadata_to_json(self):
        """Test metadata serialization to JSON."""
        metadata = AgentMetadata(
            name="test-agent",
            version="1.0.0",
            description="Test",
            author="Test",
            license="MIT",
            homepage="https://example.com",
        )

        json_str = metadata.to_json()
        data = json.loads(json_str)

        assert data["name"] == "test-agent"
        assert data["version"] == "1.0.0"

    def test_metadata_from_dict(self):
        """Test metadata deserialization from dictionary."""
        data = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "keywords": ["test"],
            "dependencies": [
                {"name": "requests", "version": ">=2.28.0", "optional": False}
            ],
        }

        metadata = AgentMetadata.from_dict(data)

        assert metadata.name == "test-agent"
        assert metadata.version == "1.0.0"
        assert len(metadata.keywords) == 1
        assert len(metadata.dependencies) == 1
        assert metadata.dependencies[0].name == "requests"

    def test_metadata_from_dict_with_rating(self):
        """Test deserialization of metadata with rating."""
        data = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "license": "MIT",
            "homepage": "https://example.com",
            "rating": {
                "average": 4.5,
                "count": 10,
                "distribution": {5: 5, 4: 3, 3: 2},
            },
        }

        metadata = AgentMetadata.from_dict(data)

        assert metadata.rating is not None
        assert metadata.rating.average == 4.5
        assert metadata.rating.count == 10


if __name__ == "__main__":
    pytest.main([__file__])
