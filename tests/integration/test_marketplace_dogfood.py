"""End-to-end dogfood test for the agent marketplace.

Exercises the full lifecycle: publish → search → install → rate → review → uninstall
using real agent packages from marketplace_agents/.
"""

from pathlib import Path

import pytest

from devloop.marketplace import RegistryClient, RegistryConfig
from devloop.marketplace.installer import AgentInstaller
from devloop.marketplace.publisher import AgentPackage, AgentPublisher
from devloop.marketplace.registry import AgentRegistry
from devloop.marketplace.reviews import ReviewStore
from devloop.marketplace.search import SearchEngine, SearchFilter


@pytest.fixture
def marketplace_dir(tmp_path: Path) -> Path:
    """Create a temporary marketplace directory."""
    mp_dir = tmp_path / "marketplace"
    mp_dir.mkdir()
    return mp_dir


@pytest.fixture
def registry(marketplace_dir: Path) -> AgentRegistry:
    config = RegistryConfig(registry_dir=marketplace_dir)
    return AgentRegistry(config)


@pytest.fixture
def client(registry: AgentRegistry) -> RegistryClient:
    return RegistryClient(registry, remote_urls=[])


@pytest.fixture
def publisher(client: RegistryClient) -> AgentPublisher:
    return AgentPublisher(client)


@pytest.fixture
def installer(client: RegistryClient, marketplace_dir: Path) -> AgentInstaller:
    return AgentInstaller(marketplace_dir / "agents", client)


@pytest.fixture
def review_store(marketplace_dir: Path) -> ReviewStore:
    return ReviewStore(marketplace_dir / "reviews")


@pytest.fixture
def agents_dir() -> Path:
    """Path to the marketplace_agents directory with real agent packages."""
    repo_root = Path(__file__).parents[2]
    agents = repo_root / "marketplace_agents"
    if not agents.exists():
        pytest.skip("marketplace_agents/ not found")
    return agents


AGENT_NAMES = [
    "devloop-formatter",
    "devloop-linter",
    "devloop-security-scanner",
    "devloop-test-runner",
]


class TestPackageValidation:
    """All packaged agents must pass validation."""

    def test_all_packages_valid(self, agents_dir: Path) -> None:
        for name in AGENT_NAMES:
            pkg = AgentPackage(agents_dir / name)
            is_valid, errors = pkg.validate()
            assert is_valid, f"{name} validation failed: {errors}"

    def test_metadata_fields_populated(self, agents_dir: Path) -> None:
        for name in AGENT_NAMES:
            pkg = AgentPackage(agents_dir / name)
            meta = pkg.metadata
            assert meta.name == name
            assert meta.version == "0.9.0"
            assert meta.author == "DevLoop"
            assert meta.license == "MIT"
            assert len(meta.categories) > 0
            assert len(meta.keywords) > 0
            assert meta.repository is not None


class TestPublishLifecycle:
    """Test publish → search → info flow."""

    def test_publish_all_agents(
        self, agents_dir: Path, publisher: AgentPublisher
    ) -> None:
        for name in AGENT_NAMES:
            success, msg = publisher.publish_agent(agents_dir / name)
            assert success, f"Failed to publish {name}: {msg}"

    def test_search_by_keyword(
        self, agents_dir: Path, publisher: AgentPublisher, registry: AgentRegistry
    ) -> None:
        for name in AGENT_NAMES:
            publisher.publish_agent(agents_dir / name)

        engine = SearchEngine()
        all_agents = registry.get_all_agents()
        results = engine.search(all_agents, SearchFilter(query="lint"))
        names = [r.name for r in results]
        assert "devloop-linter" in names

    def test_search_by_category(
        self, agents_dir: Path, publisher: AgentPublisher, registry: AgentRegistry
    ) -> None:
        for name in AGENT_NAMES:
            publisher.publish_agent(agents_dir / name)

        engine = SearchEngine()
        all_agents = registry.get_all_agents()
        results = engine.search(all_agents, SearchFilter(category="security"))
        names = [r.name for r in results]
        assert "devloop-security-scanner" in names
        assert "devloop-formatter" not in names

    def test_all_share_code_quality_category(
        self, agents_dir: Path, publisher: AgentPublisher, registry: AgentRegistry
    ) -> None:
        for name in AGENT_NAMES:
            publisher.publish_agent(agents_dir / name)

        engine = SearchEngine()
        all_agents = registry.get_all_agents()
        results = engine.search(all_agents, SearchFilter(category="code-quality"))
        assert len(results) == 4

    def test_republish_blocked_without_force(
        self, agents_dir: Path, publisher: AgentPublisher
    ) -> None:
        publisher.publish_agent(agents_dir / "devloop-formatter")
        success, msg = publisher.publish_agent(agents_dir / "devloop-formatter")
        assert not success
        assert "already published" in msg

    def test_republish_allowed_with_force(
        self, agents_dir: Path, publisher: AgentPublisher
    ) -> None:
        publisher.publish_agent(agents_dir / "devloop-formatter")
        success, msg = publisher.publish_agent(
            agents_dir / "devloop-formatter", force=True
        )
        assert success


class TestInstallLifecycle:
    """Test install → list → uninstall with dependency resolution."""

    def _publish_all(self, agents_dir: Path, publisher: AgentPublisher) -> None:
        for name in AGENT_NAMES:
            publisher.publish_agent(agents_dir / name)

    def test_install_with_dependency(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        installer: AgentInstaller,
    ) -> None:
        self._publish_all(agents_dir, publisher)

        # test-runner depends on linter
        success, msg = installer.install("devloop-test-runner")
        assert success, msg

        installed = installer.list_installed()
        names = [r.agent_name for r in installed]
        assert "devloop-test-runner" in names
        assert "devloop-linter" in names  # auto-resolved dependency

    def test_dependency_marked_correctly(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        installer: AgentInstaller,
    ) -> None:
        self._publish_all(agents_dir, publisher)
        installer.install("devloop-test-runner")

        installed = {r.agent_name: r for r in installer.list_installed()}
        assert installed["devloop-test-runner"].installed_by_user is True
        assert installed["devloop-linter"].installed_by_user is False

    def test_uninstall_blocked_by_dependent(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        installer: AgentInstaller,
    ) -> None:
        self._publish_all(agents_dir, publisher)
        installer.install("devloop-test-runner")

        # Can't uninstall linter while test-runner depends on it
        success, msg = installer.uninstall("devloop-linter")
        assert not success
        assert "depend on" in msg.lower() or "devloop-test-runner" in msg

    def test_uninstall_order(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        installer: AgentInstaller,
    ) -> None:
        self._publish_all(agents_dir, publisher)
        installer.install("devloop-test-runner")

        # Uninstall in correct order
        success, msg = installer.uninstall("devloop-test-runner")
        assert success, msg
        success, msg = installer.uninstall("devloop-linter")
        assert success, msg

        assert len(installer.list_installed()) == 0

    def test_install_standalone_agent(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        installer: AgentInstaller,
    ) -> None:
        self._publish_all(agents_dir, publisher)
        success, msg = installer.install("devloop-security-scanner")
        assert success, msg

        installed = [r.agent_name for r in installer.list_installed()]
        assert installed == ["devloop-security-scanner"]


class TestReviewLifecycle:
    """Test rate → review → query flow."""

    def _publish_all(self, agents_dir: Path, publisher: AgentPublisher) -> None:
        for name in AGENT_NAMES:
            publisher.publish_agent(agents_dir / name)

    def test_rate_agent(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        review_store: ReviewStore,
    ) -> None:
        self._publish_all(agents_dir, publisher)
        review_store.add_review(
            "devloop-formatter", "tester", 5.0, "Great", "Works perfectly"
        )
        stats = review_store.get_agent_stats("devloop-formatter")
        assert stats["average_rating"] == 5.0
        assert stats["total_reviews"] == 1

    def test_multiple_reviews(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        review_store: ReviewStore,
    ) -> None:
        self._publish_all(agents_dir, publisher)
        review_store.add_review(
            "devloop-linter", "user1", 4.0, "Good", "Fast and reliable"
        )
        review_store.add_review(
            "devloop-linter", "user2", 5.0, "Excellent", "Best linter agent"
        )
        stats = review_store.get_agent_stats("devloop-linter")
        assert stats["average_rating"] == 4.5
        assert stats["total_reviews"] == 2

    def test_review_retrieval(
        self,
        agents_dir: Path,
        publisher: AgentPublisher,
        review_store: ReviewStore,
    ) -> None:
        self._publish_all(agents_dir, publisher)
        review_store.add_review(
            "devloop-security-scanner",
            "auditor",
            5.0,
            "Catches real issues",
            "Found SQL injection that manual review missed",
        )
        reviews = review_store.get_reviews("devloop-security-scanner")
        assert len(reviews) == 1
        assert reviews[0].title == "Catches real issues"
        assert reviews[0].reviewer == "auditor"
