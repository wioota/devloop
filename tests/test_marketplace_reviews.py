"""Tests for agent marketplace reviews system."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from devloop.marketplace.reviews import Review, AgentRating, ReviewStore


@pytest.fixture
def temp_store_dir():
    """Create a temporary directory for reviews."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def review_store(temp_store_dir):
    """Create a review store."""
    return ReviewStore(temp_store_dir)


class TestReview:
    """Test review dataclass."""

    def test_create_review(self):
        """Test creating a review."""
        review = Review(
            reviewer="user1",
            rating=4.5,
            title="Great agent",
            comment="Works as expected",
            created_at=datetime.now().isoformat(),
            verified_purchase=True,
        )

        assert review.reviewer == "user1"
        assert review.rating == 4.5
        assert review.verified_purchase is True


class TestAgentRating:
    """Test agent rating functionality."""

    def test_create_rating(self):
        """Test creating an agent rating."""
        rating = AgentRating(
            agent_name="test-agent",
            average_rating=0,
            total_reviews=0,
        )

        assert rating.agent_name == "test-agent"
        assert rating.average_rating == 0
        assert len(rating.reviews) == 0

    def test_add_review_updates_stats(self):
        """Test that adding a review updates statistics."""
        rating = AgentRating(
            agent_name="test-agent",
            average_rating=0,
            total_reviews=0,
        )

        review = Review(
            reviewer="user1",
            rating=5.0,
            title="Excellent",
            comment="Perfect",
            created_at=datetime.now().isoformat(),
        )

        rating.add_review(review)

        assert rating.total_reviews == 1
        assert rating.average_rating == 5.0
        assert rating.rating_distribution[5] == 1

    def test_add_multiple_reviews(self):
        """Test adding multiple reviews."""
        rating = AgentRating(
            agent_name="test-agent",
            average_rating=0,
            total_reviews=0,
        )

        for i, score in enumerate([5, 4, 3], 1):
            review = Review(
                reviewer=f"user{i}",
                rating=float(score),
                title=f"Review {i}",
                comment="Comment",
                created_at=datetime.now().isoformat(),
            )
            rating.add_review(review)

        assert rating.total_reviews == 3
        assert rating.average_rating == 4.0

    def test_remove_review(self):
        """Test removing a review."""
        rating = AgentRating(
            agent_name="test-agent",
            average_rating=0,
            total_reviews=0,
        )

        review = Review(
            reviewer="user1",
            rating=5.0,
            title="Test",
            comment="Test",
            created_at=datetime.now().isoformat(),
        )

        rating.add_review(review)
        assert rating.total_reviews == 1

        success = rating.remove_review("user1")
        assert success is True
        assert rating.total_reviews == 0

    def test_get_reviews_by_rating(self):
        """Test filtering reviews by rating."""
        rating = AgentRating(
            agent_name="test-agent",
            average_rating=0,
            total_reviews=0,
        )

        for score in [5, 5, 4, 3]:
            review = Review(
                reviewer=f"user_{score}",
                rating=float(score),
                title="Test",
                comment="Test",
                created_at=datetime.now().isoformat(),
            )
            rating.add_review(review)

        five_star = rating.get_reviews_by_rating(5)
        assert len(five_star) == 2

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        rating = AgentRating(
            agent_name="test-agent",
            average_rating=0,
            total_reviews=0,
        )

        review = Review(
            reviewer="user1",
            rating=4.5,
            title="Great",
            comment="Good",
            created_at=datetime.now().isoformat(),
            verified_purchase=True,
        )

        rating.add_review(review)

        # Serialize
        data = rating.to_dict()
        assert data["agent_name"] == "test-agent"
        assert data["average_rating"] == 4.5
        assert len(data["reviews"]) == 1

        # Deserialize
        restored = AgentRating.from_dict(data)
        assert restored.agent_name == "test-agent"
        assert restored.average_rating == 4.5
        assert len(restored.reviews) == 1


class TestReviewStore:
    """Test review store functionality."""

    def test_store_initialization(self, temp_store_dir):
        """Test review store initialization."""
        store = ReviewStore(temp_store_dir)

        assert store.store_dir == temp_store_dir
        assert store.store_dir.exists()

    def test_add_review(self, review_store):
        """Test adding a review."""
        success = review_store.add_review(
            agent_name="agent-1",
            reviewer="user1",
            rating=5.0,
            title="Excellent",
            comment="Works great",
            verified_purchase=True,
        )

        assert success is True
        assert "agent-1" in review_store._reviews

    def test_add_invalid_rating(self, review_store):
        """Test adding review with invalid rating."""
        success = review_store.add_review(
            agent_name="agent-1",
            reviewer="user1",
            rating=6.0,  # Invalid
            title="Test",
            comment="Test",
        )

        assert success is False

    def test_update_review(self, review_store):
        """Test updating an existing review."""
        # Add first review
        review_store.add_review(
            "agent-1", "user1", 5.0, "Great", "Works well", verified_purchase=False
        )

        # Update with new rating
        review_store.add_review(
            "agent-1", "user1", 4.0, "Updated", "Changed my mind", verified_purchase=True
        )

        rating = review_store.get_rating("agent-1")
        assert rating.total_reviews == 1
        assert rating.average_rating == 4.0
        assert rating.reviews[0].verified_purchase is True

    def test_get_reviews(self, review_store):
        """Test retrieving reviews."""
        review_store.add_review("agent-1", "user1", 5.0, "T1", "C1")
        review_store.add_review("agent-1", "user2", 4.0, "T2", "C2")

        reviews = review_store.get_reviews("agent-1")

        assert len(reviews) == 2

    def test_remove_review(self, review_store):
        """Test removing a review."""
        review_store.add_review("agent-1", "user1", 5.0, "T1", "C1")

        assert review_store.get_rating("agent-1").total_reviews == 1

        success = review_store.remove_review("agent-1", "user1")
        assert success is True
        assert review_store.get_rating("agent-1").total_reviews == 0

    def test_mark_helpful(self, review_store):
        """Test marking a review as helpful."""
        review_store.add_review("agent-1", "user1", 5.0, "T1", "C1")

        success = review_store.mark_helpful("agent-1", "user1")
        assert success is True

        review = review_store.get_reviews("agent-1")[0]
        assert review.helpful_count == 1

    def test_get_recent_reviews(self, review_store):
        """Test getting recent reviews."""
        for i in range(3):
            review_store.add_review("agent-1", f"user{i}", float(i + 1), f"T{i}", f"C{i}")

        recent = review_store.get_recent_reviews("agent-1", limit=2)

        assert len(recent) == 2

    def test_get_helpful_reviews(self, review_store):
        """Test getting most helpful reviews."""
        review_store.add_review("agent-1", "user1", 5.0, "T1", "C1")
        review_store.add_review("agent-1", "user2", 4.0, "T2", "C2")

        review_store.mark_helpful("agent-1", "user1")
        review_store.mark_helpful("agent-1", "user1")
        review_store.mark_helpful("agent-1", "user2")

        helpful = review_store.get_helpful_reviews("agent-1", limit=1)

        assert helpful[0].reviewer == "user1"
        assert helpful[0].helpful_count == 2

    def test_get_agent_stats(self, review_store):
        """Test getting agent statistics."""
        review_store.add_review("agent-1", "user1", 5.0, "T1", "C1", verified_purchase=True)
        review_store.add_review("agent-1", "user2", 4.0, "T2", "C2", verified_purchase=False)

        stats = review_store.get_agent_stats("agent-1")

        assert stats["agent_name"] == "agent-1"
        assert stats["average_rating"] == 4.5
        assert stats["total_reviews"] == 2
        assert stats["verified_purchases"] == 1

    def test_get_stats(self, review_store):
        """Test getting overall statistics."""
        review_store.add_review("agent-1", "user1", 5.0, "T1", "C1")
        review_store.add_review("agent-2", "user1", 4.0, "T1", "C1")

        stats = review_store.get_stats()

        assert stats["total_reviews"] == 2
        assert stats["agents_reviewed"] == 2
        assert stats["overall_average_rating"] == 4.5

    def test_persistence(self, temp_store_dir):
        """Test that reviews persist to disk."""
        # Create and populate store
        store1 = ReviewStore(temp_store_dir)
        store1.add_review("agent-1", "user1", 5.0, "Great", "Works", verified_purchase=True)

        # Create new store from same directory
        store2 = ReviewStore(temp_store_dir)

        # Should have loaded the previous review
        rating = store2.get_rating("agent-1")
        assert rating is not None
        assert rating.total_reviews == 1
        assert rating.reviews[0].verified_purchase is True

    def test_rating_distribution(self, review_store):
        """Test rating distribution tracking."""
        ratings = [5, 5, 4, 4, 4, 3, 2]
        for i, r in enumerate(ratings):
            review_store.add_review(f"agent-1", f"user{i}", float(r), "T", "C")

        stats = review_store.get_agent_stats("agent-1")

        assert stats["rating_distribution"][5] == 2
        assert stats["rating_distribution"][4] == 3
        assert stats["rating_distribution"][3] == 1
        assert stats["rating_distribution"][2] == 1


if __name__ == "__main__":
    pytest.main([__file__])
