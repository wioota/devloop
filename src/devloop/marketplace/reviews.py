"""User reviews and ratings system for agents."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json
import logging


logger = logging.getLogger(__name__)


@dataclass
class Review:
    """A user review for an agent."""

    reviewer: str  # Username or identifier
    rating: float  # 1-5 stars
    title: str  # Review title
    comment: str  # Review text
    created_at: str
    updated_at: Optional[str] = None
    helpful_count: int = 0  # Number of users who found helpful
    verified_purchase: bool = False  # User actually installed the agent


@dataclass
class AgentRating:
    """Aggregated rating data for an agent."""

    agent_name: str
    average_rating: float
    total_reviews: int
    rating_distribution: Dict[int, int] = field(
        default_factory=dict
    )  # {1: count, 2: count, ...}
    reviews: List[Review] = field(default_factory=list)

    def add_review(self, review: Review) -> None:
        """Add a review and update aggregate stats."""
        self.reviews.append(review)

        # Update distribution
        rating_int = int(review.rating)
        self.rating_distribution[rating_int] = (
            self.rating_distribution.get(rating_int, 0) + 1
        )

        # Recalculate average
        self.total_reviews = len(self.reviews)
        if self.total_reviews > 0:
            total_stars = sum(r.rating for r in self.reviews)
            self.average_rating = round(total_stars / self.total_reviews, 2)

    def remove_review(self, reviewer: str) -> bool:
        """Remove a review by reviewer."""
        for i, review in enumerate(self.reviews):
            if review.reviewer == reviewer:
                removed = self.reviews.pop(i)

                # Update distribution
                rating_int = int(removed.rating)
                if rating_int in self.rating_distribution:
                    self.rating_distribution[rating_int] -= 1
                    if self.rating_distribution[rating_int] == 0:
                        del self.rating_distribution[rating_int]

                # Recalculate average
                self.total_reviews = len(self.reviews)
                if self.total_reviews > 0:
                    total_stars = sum(r.rating for r in self.reviews)
                    self.average_rating = round(total_stars / self.total_reviews, 2)
                else:
                    self.average_rating = 0

                return True
        return False

    def get_reviews_by_rating(self, rating: int) -> List[Review]:
        """Get all reviews with a specific rating."""
        return [r for r in self.reviews if int(r.rating) == rating]

    def get_recent_reviews(self, limit: int = 10) -> List[Review]:
        """Get most recent reviews."""
        sorted_reviews = sorted(self.reviews, key=lambda r: r.created_at, reverse=True)
        return sorted_reviews[:limit]

    def get_helpful_reviews(self, limit: int = 10) -> List[Review]:
        """Get most helpful (by helpful_count) reviews."""
        sorted_reviews = sorted(
            self.reviews, key=lambda r: r.helpful_count, reverse=True
        )
        return sorted_reviews[:limit]

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "agent_name": self.agent_name,
            "average_rating": self.average_rating,
            "total_reviews": self.total_reviews,
            "rating_distribution": self.rating_distribution,
            "reviews": [
                {
                    "reviewer": r.reviewer,
                    "rating": r.rating,
                    "title": r.title,
                    "comment": r.comment,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "helpful_count": r.helpful_count,
                    "verified_purchase": r.verified_purchase,
                }
                for r in self.reviews
            ],
        }

    @staticmethod
    def from_dict(data: Dict) -> "AgentRating":
        """Deserialize from dictionary."""
        reviews = [
            Review(
                reviewer=r["reviewer"],
                rating=r["rating"],
                title=r["title"],
                comment=r["comment"],
                created_at=r["created_at"],
                updated_at=r.get("updated_at"),
                helpful_count=r.get("helpful_count", 0),
                verified_purchase=r.get("verified_purchase", False),
            )
            for r in data.get("reviews", [])
        ]

        return AgentRating(
            agent_name=data["agent_name"],
            average_rating=data.get("average_rating", 0),
            total_reviews=data.get("total_reviews", 0),
            rating_distribution=data.get("rating_distribution", {}),
            reviews=reviews,
        )


class ReviewStore:
    """Store and manage agent reviews."""

    def __init__(self, store_dir: Path):
        """Initialize review store."""
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._reviews: Dict[str, AgentRating] = {}
        self._load_reviews()

    def _get_review_file(self, agent_name: str) -> Path:
        """Get path to review file for an agent."""
        safe_name = agent_name.replace("/", "_")
        return self.store_dir / f"{safe_name}_reviews.json"

    def _load_reviews(self) -> None:
        """Load all reviews from disk."""
        for review_file in self.store_dir.glob("*_reviews.json"):
            try:
                with open(review_file) as f:
                    data = json.load(f)
                rating = AgentRating.from_dict(data)
                self._reviews[rating.agent_name] = rating
            except Exception as e:
                logger.warning(f"Failed to load reviews from {review_file}: {e}")

    def _save_reviews(self, agent_name: str) -> bool:
        """Save reviews for an agent to disk."""
        if agent_name not in self._reviews:
            return False

        review_file = self._get_review_file(agent_name)
        try:
            with open(review_file, "w") as f:
                json.dump(self._reviews[agent_name].to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save reviews for {agent_name}: {e}")
            return False

    def add_review(
        self,
        agent_name: str,
        reviewer: str,
        rating: float,
        title: str,
        comment: str,
        verified_purchase: bool = False,
    ) -> bool:
        """Add a review for an agent."""
        # Validate rating
        if not 1 <= rating <= 5:
            logger.error(f"Invalid rating: {rating}")
            return False

        # Get or create rating
        if agent_name not in self._reviews:
            self._reviews[agent_name] = AgentRating(
                agent_name=agent_name,
                average_rating=0,
                total_reviews=0,
            )

        # Check if reviewer already has a review
        existing_review = None
        for review in self._reviews[agent_name].reviews:
            if review.reviewer == reviewer:
                existing_review = review
                break

        if existing_review:
            # Update existing review - remove old rating first
            old_rating_int = int(existing_review.rating)
            if old_rating_int in self._reviews[agent_name].rating_distribution:
                self._reviews[agent_name].rating_distribution[old_rating_int] -= 1
                if self._reviews[agent_name].rating_distribution[old_rating_int] == 0:
                    del self._reviews[agent_name].rating_distribution[old_rating_int]

            # Update review
            existing_review.rating = rating
            existing_review.title = title
            existing_review.comment = comment
            existing_review.updated_at = datetime.now().isoformat()
            existing_review.verified_purchase = verified_purchase

            # Add new rating to distribution
            new_rating_int = int(rating)
            self._reviews[agent_name].rating_distribution[new_rating_int] = (
                self._reviews[agent_name].rating_distribution.get(new_rating_int, 0) + 1
            )

            # Recalculate average
            self._reviews[agent_name].total_reviews = len(
                self._reviews[agent_name].reviews
            )
            if self._reviews[agent_name].total_reviews > 0:
                total_stars = sum(r.rating for r in self._reviews[agent_name].reviews)
                self._reviews[agent_name].average_rating = round(
                    total_stars / self._reviews[agent_name].total_reviews, 2
                )

            logger.info(f"Updated review for {agent_name} by {reviewer}")
        else:
            # Add new review
            review = Review(
                reviewer=reviewer,
                rating=rating,
                title=title,
                comment=comment,
                created_at=datetime.now().isoformat(),
                verified_purchase=verified_purchase,
            )
            self._reviews[agent_name].add_review(review)
            logger.info(f"Added review for {agent_name} by {reviewer}")

        self._save_reviews(agent_name)
        return True

    def get_rating(self, agent_name: str) -> Optional[AgentRating]:
        """Get rating data for an agent."""
        return self._reviews.get(agent_name)

    def get_reviews(self, agent_name: str) -> List[Review]:
        """Get all reviews for an agent."""
        if agent_name not in self._reviews:
            return []
        return self._reviews[agent_name].reviews

    def get_recent_reviews(self, agent_name: str, limit: int = 10) -> List[Review]:
        """Get recent reviews for an agent."""
        rating = self._reviews.get(agent_name)
        if not rating:
            return []
        return rating.get_recent_reviews(limit)

    def get_helpful_reviews(self, agent_name: str, limit: int = 10) -> List[Review]:
        """Get most helpful reviews for an agent."""
        rating = self._reviews.get(agent_name)
        if not rating:
            return []
        return rating.get_helpful_reviews(limit)

    def remove_review(self, agent_name: str, reviewer: str) -> bool:
        """Remove a review."""
        if agent_name not in self._reviews:
            return False

        if self._reviews[agent_name].remove_review(reviewer):
            self._save_reviews(agent_name)
            logger.info(f"Removed review for {agent_name} by {reviewer}")
            return True

        return False

    def mark_helpful(self, agent_name: str, reviewer: str) -> bool:
        """Mark a review as helpful."""
        if agent_name not in self._reviews:
            return False

        for review in self._reviews[agent_name].reviews:
            if review.reviewer == reviewer:
                review.helpful_count += 1
                self._save_reviews(agent_name)
                return True

        return False

    def get_agent_stats(self, agent_name: str) -> Dict:
        """Get rating statistics for an agent."""
        rating = self._reviews.get(agent_name)
        if not rating:
            return {
                "agent_name": agent_name,
                "average_rating": 0,
                "total_reviews": 0,
                "rating_distribution": {},
            }

        return {
            "agent_name": agent_name,
            "average_rating": rating.average_rating,
            "total_reviews": rating.total_reviews,
            "rating_distribution": rating.rating_distribution,
            "verified_purchases": sum(1 for r in rating.reviews if r.verified_purchase),
        }

    def get_stats(self) -> Dict:
        """Get overall review statistics."""
        total_reviews = sum(r.total_reviews for r in self._reviews.values())
        agents_with_reviews = len(
            [r for r in self._reviews.values() if r.total_reviews > 0]
        )

        avg_ratings = [
            r.average_rating for r in self._reviews.values() if r.total_reviews > 0
        ]
        overall_avg = (
            round(sum(avg_ratings) / len(avg_ratings), 2) if avg_ratings else 0
        )

        return {
            "total_reviews": total_reviews,
            "agents_reviewed": agents_with_reviews,
            "overall_average_rating": overall_avg,
            "storage_location": str(self.store_dir),
        }
