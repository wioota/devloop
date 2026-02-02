"""Tests for marketplace CLI commands."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from devloop.cli.commands.marketplace import (
    categories,
    get_marketplace_dir,
    get_registry_client,
    info,
    install,
    list as list_cmd,
    list_installed,
    rate,
    review,
    review_details,
    review_stats,
    reviews,
    search,
    stats,
    uninstall,
)


@pytest.fixture
def mock_console():
    """Mock rich console."""
    with patch("devloop.cli.commands.marketplace.console") as mock:
        yield mock


@pytest.fixture
def mock_client():
    """Create mock registry client."""
    return Mock()


@pytest.fixture
def mock_installer():
    """Create mock agent installer."""
    return Mock()


@pytest.fixture
def mock_review_store():
    """Create mock review store."""
    return Mock()


@pytest.fixture
def sample_agent():
    """Sample agent metadata for testing."""
    agent = Mock()
    agent.name = "test-agent"
    agent.version = "1.0.0"
    agent.author = "Test Author"
    agent.license = "MIT"
    agent.description = "A test agent"
    agent.homepage = "https://example.com"
    agent.repository = "https://github.com/test/test-agent"
    agent.categories = ["testing", "utilities"]
    agent.keywords = ["test", "example"]
    agent.rating = Mock(average=4.5, count=100)
    agent.downloads = 1000
    agent.trusted = True
    agent.experimental = False
    agent.deprecated = False
    agent.deprecation_message = None
    agent.python_version = ">=3.8"
    agent.devloop_version = ">=0.5.0"
    agent.dependencies = []
    return agent


class TestGetMarketplaceDir:
    """Tests for get_marketplace_dir function."""

    def test_returns_devloop_marketplace_path(self):
        """Test that marketplace dir is in ~/.devloop/marketplace."""
        result = get_marketplace_dir()
        assert result == Path.home() / ".devloop" / "marketplace"


class TestGetRegistryClient:
    """Tests for get_registry_client function."""

    def test_creates_registry_client(self):
        """Test that registry client is created."""
        with patch("devloop.cli.commands.marketplace.RegistryConfig"):
            with patch("devloop.cli.commands.marketplace.AgentRegistry"):
                with patch(
                    "devloop.cli.commands.marketplace.RegistryClient"
                ) as mock_client_cls:
                    get_registry_client()
                    mock_client_cls.assert_called_once()


class TestSearchCommand:
    """Tests for search command."""

    def test_search_no_results(self, mock_console, mock_client):
        """Test search with no results."""
        mock_client.search.return_value = {"local": [], "remote": []}

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            search(
                query="nonexistent",
                category=None,
                min_rating=0.0,
                limit=20,
                remote=True,
            )

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "No agents found" in call_args

    def test_search_with_results(self, mock_console, mock_client, sample_agent):
        """Test search with results."""
        mock_client.search.return_value = {"local": [sample_agent], "remote": []}

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            search(
                query="test",
                category=None,
                min_rating=0.0,
                limit=20,
                remote=True,
            )

        mock_client.search.assert_called_once_with(
            "test",
            search_remote=True,
            categories=None,
            min_rating=0.0,
            max_results=20,
        )
        mock_console.print.assert_called()

    def test_search_with_category_filter(self, mock_console, mock_client, sample_agent):
        """Test search with category filter."""
        mock_client.search.return_value = {"local": [sample_agent], "remote": []}

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            search(
                query="test",
                category="testing",
                min_rating=0.0,
                limit=20,
                remote=True,
            )

        mock_client.search.assert_called_once_with(
            "test",
            search_remote=True,
            categories=["testing"],
            min_rating=0.0,
            max_results=20,
        )

    def test_search_with_min_rating(self, mock_console, mock_client, sample_agent):
        """Test search with minimum rating filter."""
        mock_client.search.return_value = {"local": [sample_agent], "remote": []}

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            search(
                query="test",
                category=None,
                min_rating=4.0,
                limit=20,
                remote=True,
            )

        mock_client.search.assert_called_once_with(
            "test",
            search_remote=True,
            categories=None,
            min_rating=4.0,
            max_results=20,
        )

    def test_search_local_only(self, mock_console, mock_client, sample_agent):
        """Test search without remote registries."""
        mock_client.search.return_value = {"local": [sample_agent], "remote": []}

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            search(
                query="test",
                category=None,
                min_rating=0.0,
                limit=20,
                remote=False,
            )

        mock_client.search.assert_called_once_with(
            "test",
            search_remote=False,
            categories=None,
            min_rating=0.0,
            max_results=20,
        )


class TestInfoCommand:
    """Tests for info command."""

    def test_info_agent_not_found(self, mock_console, mock_client):
        """Test info when agent not found."""
        mock_client.get_agent.return_value = None

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            info(name="nonexistent", version=None)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "Agent not found" in call_args

    def test_info_displays_agent_details(self, mock_console, mock_client, sample_agent):
        """Test info displays agent details."""
        mock_client.get_agent.return_value = sample_agent

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            info(name="test-agent", version=None)

        mock_client.get_agent.assert_called_once_with("test-agent", None)
        mock_console.print.assert_called()

    def test_info_with_specific_version(self, mock_console, mock_client, sample_agent):
        """Test info with specific version."""
        mock_client.get_agent.return_value = sample_agent

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            info(name="test-agent", version="1.0.0")

        mock_client.get_agent.assert_called_once_with("test-agent", "1.0.0")

    def test_info_deprecated_agent(self, mock_console, mock_client, sample_agent):
        """Test info for deprecated agent."""
        sample_agent.deprecated = True
        sample_agent.deprecation_message = "Use new-agent instead"
        mock_client.get_agent.return_value = sample_agent

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            info(name="test-agent", version=None)

        mock_console.print.assert_called()

    def test_info_experimental_agent(self, mock_console, mock_client, sample_agent):
        """Test info for experimental agent."""
        sample_agent.trusted = False
        sample_agent.experimental = True
        mock_client.get_agent.return_value = sample_agent

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            info(name="test-agent", version=None)

        mock_console.print.assert_called()


class TestListCommand:
    """Tests for list command."""

    def test_list_no_agents(self, mock_console, mock_client):
        """Test list with no agents."""
        mock_client.get_popular_agents.return_value = []

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            list_cmd(category=None, limit=20, sort="rating")

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "No agents found" in call_args

    def test_list_popular_agents(self, mock_console, mock_client, sample_agent):
        """Test list shows popular agents by default."""
        mock_client.get_popular_agents.return_value = [sample_agent]

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            list_cmd(category=None, limit=20, sort="rating")

        mock_client.get_popular_agents.assert_called_once_with(limit=20)
        mock_console.print.assert_called()

    def test_list_by_category(self, mock_console, mock_client, sample_agent):
        """Test list agents by category."""
        mock_client.get_agents_by_category.return_value = [sample_agent]

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            list_cmd(category="testing", limit=20, sort="rating")

        mock_client.get_agents_by_category.assert_called_once_with("testing", limit=20)


class TestCategoriesCommand:
    """Tests for categories command."""

    def test_categories_no_categories(self, mock_console, mock_client):
        """Test categories with no categories available."""
        mock_client.get_categories.return_value = {}

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            categories()

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "No categories" in call_args

    def test_categories_shows_all(self, mock_console, mock_client):
        """Test categories shows all categories."""
        mock_client.get_categories.return_value = {
            "testing": 10,
            "utilities": 5,
            "formatters": 3,
        }

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            categories()

        mock_console.print.assert_called()


class TestRateCommand:
    """Tests for rate command."""

    def test_rate_invalid_rating_low(self, mock_console, mock_client):
        """Test rate with rating below 1."""
        rate(name="test-agent", rating=0)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "between 1 and 5" in call_args

    def test_rate_invalid_rating_high(self, mock_console, mock_client):
        """Test rate with rating above 5."""
        rate(name="test-agent", rating=6)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "between 1 and 5" in call_args

    def test_rate_success(self, mock_console, mock_client, sample_agent):
        """Test successful rating."""
        mock_client.rate_agent.return_value = True
        mock_client.get_agent.return_value = sample_agent

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            rate(name="test-agent", rating=5)

        mock_client.rate_agent.assert_called_once_with("test-agent", 5)

    def test_rate_failure(self, mock_console, mock_client):
        """Test failed rating."""
        mock_client.rate_agent.return_value = False

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            rate(name="test-agent", rating=5)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "Failed" in call_args


class TestStatsCommand:
    """Tests for stats command."""

    def test_stats_displays_stats(self, mock_console, mock_client):
        """Test stats displays marketplace statistics."""
        mock_client.get_registry_stats.return_value = {
            "local": {
                "total_agents": 100,
                "active_agents": 80,
                "trusted_agents": 50,
                "total_downloads": 10000,
                "average_rating": 4.2,
                "categories": {"testing": 30, "utilities": 20},
            }
        }

        with patch(
            "devloop.cli.commands.marketplace.get_registry_client",
            return_value=mock_client,
        ):
            stats()

        mock_console.print.assert_called()


class TestInstallCommand:
    """Tests for install command."""

    def test_install_success(self, mock_console, mock_installer):
        """Test successful installation."""
        mock_installer.install.return_value = (
            True,
            "Successfully installed test-agent",
        )

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            install(name="test-agent", version=None, force=False)

        mock_installer.install.assert_called_once_with("test-agent", None, force=False)
        mock_console.print.assert_called()

    def test_install_failure(self, mock_console, mock_installer):
        """Test failed installation."""
        mock_installer.install.return_value = (False, "Agent not found")

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            install(name="nonexistent", version=None, force=False)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "Agent not found" in call_args

    def test_install_with_version(self, mock_console, mock_installer):
        """Test installation with specific version."""
        mock_installer.install.return_value = (True, "Installed")

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            install(name="test-agent", version="1.0.0", force=False)

        mock_installer.install.assert_called_once_with(
            "test-agent", "1.0.0", force=False
        )

    def test_install_force(self, mock_console, mock_installer):
        """Test forced installation."""
        mock_installer.install.return_value = (True, "Reinstalled")

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            install(name="test-agent", version=None, force=True)

        mock_installer.install.assert_called_once_with("test-agent", None, force=True)


class TestUninstallCommand:
    """Tests for uninstall command."""

    def test_uninstall_success(self, mock_console, mock_installer):
        """Test successful uninstallation."""
        mock_installer.uninstall.return_value = (True, "Uninstalled test-agent")

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            uninstall(name="test-agent", force=False)

        mock_installer.uninstall.assert_called_once_with(
            "test-agent", remove_dependencies=False
        )

    def test_uninstall_failure(self, mock_console, mock_installer):
        """Test failed uninstallation."""
        mock_installer.uninstall.return_value = (False, "Agent not installed")

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            uninstall(name="nonexistent", force=False)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "not installed" in call_args

    def test_uninstall_force(self, mock_console, mock_installer):
        """Test forced uninstallation."""
        mock_installer.uninstall.return_value = (True, "Uninstalled")

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            uninstall(name="test-agent", force=True)

        mock_installer.uninstall.assert_called_once_with(
            "test-agent", remove_dependencies=True
        )


class TestListInstalledCommand:
    """Tests for list_installed command."""

    def test_list_installed_empty(self, mock_console, mock_installer):
        """Test list_installed with no agents."""
        mock_installer.list_installed.return_value = []

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            list_installed()

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "No agents installed" in call_args

    def test_list_installed_shows_agents(self, mock_console, mock_installer):
        """Test list_installed shows installed agents."""
        mock_record = Mock()
        mock_record.agent_name = "test-agent"
        mock_record.version = "1.0.0"
        mock_record.installed_at = "2024-01-15T10:30:00Z"
        mock_record.installed_by_user = True
        mock_installer.list_installed.return_value = [mock_record]

        with patch(
            "devloop.cli.commands.marketplace._get_installer",
            return_value=mock_installer,
        ):
            list_installed()

        mock_console.print.assert_called()


class TestReviewCommand:
    """Tests for review command."""

    def test_review_invalid_rating_low(self, mock_console):
        """Test review with rating below 1."""
        review(name="test-agent", rating=0, title="Bad", comment="Test", verified=False)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "between 1 and 5" in call_args

    def test_review_invalid_rating_high(self, mock_console):
        """Test review with rating above 5."""
        review(name="test-agent", rating=6, title="Bad", comment="Test", verified=False)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "between 1 and 5" in call_args

    def test_review_success(self, mock_console, mock_review_store):
        """Test successful review."""
        mock_review_store.add_review.return_value = True
        mock_review_store.get_agent_stats.return_value = {
            "average_rating": 4.5,
            "total_reviews": 10,
        }

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review(
                name="test-agent",
                rating=5,
                title="Great agent!",
                comment="Works perfectly",
                verified=True,
            )

        mock_review_store.add_review.assert_called_once()

    def test_review_failure(self, mock_console, mock_review_store):
        """Test failed review."""
        mock_review_store.add_review.return_value = False

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review(
                name="test-agent",
                rating=5,
                title="Good",
                comment="Test",
                verified=False,
            )

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "Failed" in call_args


class TestReviewsCommand:
    """Tests for reviews command."""

    def test_reviews_no_reviews(self, mock_console, mock_review_store):
        """Test reviews with no reviews."""
        mock_review_store.get_agent_stats.return_value = {"total_reviews": 0}

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            reviews(name="test-agent", limit=10, sort="recent")

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "No reviews" in call_args

    def test_reviews_shows_reviews(self, mock_console, mock_review_store):
        """Test reviews shows list of reviews."""
        mock_review_store.get_agent_stats.return_value = {
            "average_rating": 4.5,
            "total_reviews": 5,
        }
        mock_review = Mock()
        mock_review.rating = 5
        mock_review.title = "Great!"
        mock_review.reviewer = "user1"
        mock_review.verified_purchase = True
        mock_review.helpful_count = 10
        mock_review_store.get_recent_reviews.return_value = [mock_review]

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            reviews(name="test-agent", limit=10, sort="recent")

        mock_console.print.assert_called()

    def test_reviews_sort_by_helpful(self, mock_console, mock_review_store):
        """Test reviews sorted by helpful count."""
        mock_review_store.get_agent_stats.return_value = {
            "average_rating": 4.5,
            "total_reviews": 5,
        }
        mock_review = Mock()
        mock_review.rating = 5
        mock_review.title = "Great!"
        mock_review.reviewer = "user1"
        mock_review.verified_purchase = False
        mock_review.helpful_count = 10
        mock_review_store.get_helpful_reviews.return_value = [mock_review]

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            reviews(name="test-agent", limit=10, sort="helpful")

        mock_review_store.get_helpful_reviews.assert_called_once_with("test-agent", 10)


class TestReviewDetailsCommand:
    """Tests for review_details command."""

    def test_review_details_no_reviews(self, mock_console, mock_review_store):
        """Test review_details with no reviews."""
        mock_review_store.get_reviews.return_value = []

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review_details(name="test-agent", reviewer=None)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "No reviews" in call_args

    def test_review_details_shows_reviews(self, mock_console, mock_review_store):
        """Test review_details shows full review content."""
        mock_review = Mock()
        mock_review.rating = 5
        mock_review.title = "Great agent!"
        mock_review.reviewer = "user1"
        mock_review.verified_purchase = True
        mock_review.helpful_count = 10
        mock_review.created_at = "2024-01-15T10:30:00Z"
        mock_review.comment = "Works perfectly"
        mock_review_store.get_reviews.return_value = [mock_review]

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review_details(name="test-agent", reviewer=None)

        mock_console.print.assert_called()

    def test_review_details_filter_by_reviewer(self, mock_console, mock_review_store):
        """Test review_details filters by reviewer."""
        mock_review = Mock()
        mock_review.rating = 5
        mock_review.title = "Great!"
        mock_review.reviewer = "user1"
        mock_review.verified_purchase = True
        mock_review.helpful_count = 10
        mock_review.created_at = "2024-01-15T10:30:00Z"
        mock_review.comment = "Test"
        mock_review_store.get_reviews.return_value = [mock_review]

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review_details(name="test-agent", reviewer="user1")

        mock_review_store.get_reviews.assert_called_once_with("test-agent")


class TestReviewStatsCommand:
    """Tests for review_stats command."""

    def test_review_stats_for_agent(self, mock_console, mock_review_store):
        """Test review_stats for specific agent."""
        mock_review_store.get_agent_stats.return_value = {
            "average_rating": 4.5,
            "total_reviews": 10,
            "verified_purchases": 5,
            "rating_distribution": {5: 6, 4: 3, 3: 1},
        }

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review_stats(name="test-agent")

        mock_review_store.get_agent_stats.assert_called_once_with("test-agent")
        mock_console.print.assert_called()

    def test_review_stats_overall(self, mock_console, mock_review_store):
        """Test review_stats overall statistics."""
        mock_review_store.get_stats.return_value = {
            "total_reviews": 100,
            "agents_reviewed": 50,
            "overall_average_rating": 4.2,
        }

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review_stats(name=None)

        mock_review_store.get_stats.assert_called_once()
        mock_console.print.assert_called()

    def test_review_stats_empty_distribution(self, mock_console, mock_review_store):
        """Test review_stats with empty rating distribution."""
        mock_review_store.get_agent_stats.return_value = {
            "average_rating": 0.0,
            "total_reviews": 0,
            "verified_purchases": 0,
            "rating_distribution": {},
        }

        with patch(
            "devloop.cli.commands.marketplace._get_review_store",
            return_value=mock_review_store,
        ):
            review_stats(name="test-agent")

        mock_console.print.assert_called()
