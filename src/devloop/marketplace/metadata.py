"""Agent metadata schema and validation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json
from pathlib import Path


@dataclass
class Dependency:
    """Agent dependency specification."""

    name: str
    version: str  # Semantic version constraint (e.g., ">=1.0.0,<2.0.0")
    optional: bool = False
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "optional": self.optional,
            "description": self.description,
        }


@dataclass
class Rating:
    """Agent rating information."""

    average: float  # 1-5 stars
    count: int  # Number of ratings
    distribution: Dict[int, int] = field(default_factory=dict)  # {rating: count}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "average": round(self.average, 2),
            "count": self.count,
            "distribution": self.distribution,
        }


@dataclass
class AgentMetadata:
    """Complete agent metadata for registry."""

    # Required fields
    name: str  # Unique identifier (e.g., "my-custom-linter")
    version: str  # Semantic version (e.g., "1.0.0")
    description: str  # Short description (max 500 chars)
    author: str  # Author name or organization
    license: str  # SPDX license identifier

    # Optional but recommended
    homepage: Optional[str] = None
    repository: Optional[str] = None
    documentation: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(
        default_factory=list
    )  # e.g., ["linting", "formatting"]

    # Requirements
    python_version: str = ">=3.11"  # Semantic version constraint
    devloop_version: str = ">=0.5.0"  # Minimum devloop version
    dependencies: List[Dependency] = field(default_factory=list)

    # Marketplace metadata
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    downloads: int = 0
    rating: Optional[Rating] = None

    # Additional metadata
    trusted: bool = False  # Marked as trusted by maintainers
    experimental: bool = False  # Beta/experimental agent
    deprecated: bool = False
    deprecation_message: Optional[str] = None

    # Custom metadata
    custom: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMetadata":
        """Create metadata from dictionary."""
        # Parse dependencies
        deps = []
        for dep_data in data.get("dependencies", []):
            deps.append(Dependency(**dep_data))

        # Parse rating
        rating = None
        if "rating" in data and data["rating"]:
            rating_data = data["rating"]
            rating = Rating(
                average=rating_data.get("average", 0),
                count=rating_data.get("count", 0),
                distribution=rating_data.get("distribution", {}),
            )

        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            license=data["license"],
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            documentation=data.get("documentation"),
            keywords=data.get("keywords", []),
            categories=data.get("categories", []),
            python_version=data.get("python_version", ">=3.11"),
            devloop_version=data.get("devloop_version", ">=0.5.0"),
            dependencies=deps,
            published_at=data.get("published_at"),
            updated_at=data.get("updated_at"),
            downloads=data.get("downloads", 0),
            rating=rating,
            trusted=data.get("trusted", False),
            experimental=data.get("experimental", False),
            deprecated=data.get("deprecated", False),
            deprecation_message=data.get("deprecation_message"),
            custom=data.get("custom", {}),
        )

    @classmethod
    def from_json_file(cls, path: Path) -> "AgentMetadata":
        """Load metadata from JSON file (agent.json)."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
        }

        if self.homepage:
            data["homepage"] = self.homepage
        if self.repository:
            data["repository"] = self.repository
        if self.documentation:
            data["documentation"] = self.documentation
        if self.keywords:
            data["keywords"] = self.keywords
        if self.categories:
            data["categories"] = self.categories

        data["python_version"] = self.python_version
        data["devloop_version"] = self.devloop_version

        if self.dependencies:
            data["dependencies"] = [d.to_dict() for d in self.dependencies]

        if self.published_at:
            data["published_at"] = self.published_at
        if self.updated_at:
            data["updated_at"] = self.updated_at

        if self.downloads:
            data["downloads"] = self.downloads
        if self.rating:
            data["rating"] = self.rating.to_dict()

        if self.trusted:
            data["trusted"] = True
        if self.experimental:
            data["experimental"] = True
        if self.deprecated:
            data["deprecated"] = True
        if self.deprecation_message:
            data["deprecation_message"] = self.deprecation_message

        if self.custom:
            data["custom"] = self.custom

        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def validate(self) -> List[str]:
        """Validate metadata. Returns list of validation errors."""
        errors = []

        # Required fields
        if not self.name or not self.name.strip():
            errors.append("name is required")
        if not self.version or not self.version.strip():
            errors.append("version is required")
        if not self.description or not self.description.strip():
            errors.append("description is required")
        if len(self.description) > 500:
            errors.append("description must be <= 500 characters")
        if not self.author or not self.author.strip():
            errors.append("author is required")
        if not self.license or not self.license.strip():
            errors.append("license is required")

        # Name validation (alphanumeric, dash, underscore)
        if self.name and not all(c.isalnum() or c in "-_" for c in self.name):
            errors.append(
                "name must contain only alphanumeric characters, dashes, and underscores"
            )

        # Version validation (basic semantic versioning)
        if self.version and not _is_valid_version(self.version):
            errors.append("version must be valid semantic version (e.g., 1.0.0)")

        if not self.homepage and not self.repository:
            errors.append("either homepage or repository is required")

        return errors


def _is_valid_version(version: str) -> bool:
    """Check if version is valid semantic versioning."""
    parts = version.split(".")
    if len(parts) != 3:
        return False
    return all(part.isdigit() for part in parts)
