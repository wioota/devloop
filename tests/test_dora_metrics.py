"""Tests for DORA metrics analysis."""

import subprocess
from datetime import datetime, UTC, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from devloop.metrics.dora import GitAnalyzer, DORAMetricsAnalyzer


@pytest.fixture
def git_repo():
    """Create a temporary git repository with some commits."""
    with TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        
        # Configure git user
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        
        # Create initial commit
        test_file = repo_path / "test.txt"
        test_file.write_text("initial content\n")
        
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        
        # Create a few more commits
        for i in range(3):
            test_file.write_text(f"content v{i}\n")
            subprocess.run(
                ["git", "add", "test.txt"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Commit {i}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        
        # Create a release tag
        subprocess.run(
            ["git", "tag", "v1.0.0"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        
        yield repo_path


def test_git_analyzer_initialization(git_repo):
    """Test GitAnalyzer initialization."""
    analyzer = GitAnalyzer(git_repo)
    assert analyzer.repo_path == git_repo


def test_git_analyzer_invalid_repo():
    """Test GitAnalyzer with invalid repository."""
    with TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="Not a git repository"):
            GitAnalyzer(Path(tmpdir))


def test_get_commits_in_range(git_repo):
    """Test getting commits in a date range."""
    analyzer = GitAnalyzer(git_repo)
    
    start = datetime.now(UTC) - timedelta(days=2)
    end = datetime.now(UTC) + timedelta(days=2)
    
    commits = analyzer.get_commits_in_range(start, end, branch="master")
    
    # Should have at least 1 commit (git creates at least 1 when we commit)
    assert len(commits) >= 1
    
    # Check commit structure
    for commit in commits:
        assert commit.hash
        assert commit.message
        assert commit.author
        assert commit.timestamp


def test_get_tags_in_range(git_repo):
    """Test getting tags in a date range."""
    analyzer = GitAnalyzer(git_repo)
    
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC) + timedelta(days=1)
    
    tags = analyzer.get_tags_in_range(start, end)
    
    # Should have at least the v1.0.0 tag
    assert len(tags) >= 1
    assert any(tag.tag == "v1.0.0" for tag in tags)
    
    # Check tag structure
    for tag in tags:
        assert tag.tag
        assert tag.hash
        assert tag.timestamp


def test_get_deployment_frequency(git_repo):
    """Test deployment frequency calculation."""
    analyzer = GitAnalyzer(git_repo)
    
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC) + timedelta(days=1)
    
    metrics = analyzer.get_deployment_frequency(start, end)
    
    assert metrics.deployments_count >= 0
    assert metrics.deployment_frequency >= 0
    assert metrics.period_days > 0


def test_get_lead_time_for_changes(git_repo):
    """Test lead time for changes calculation."""
    analyzer = GitAnalyzer(git_repo)
    
    start = datetime.now(UTC) - timedelta(days=1)
    end = datetime.now(UTC) + timedelta(days=1)
    
    metrics = analyzer.get_lead_time_for_changes(start, end, branch="master")
    
    # Might be None if not enough commits
    if metrics:
        assert metrics.avg_lead_time_hours >= 0
        assert metrics.min_lead_time_hours >= 0
        assert metrics.max_lead_time_hours >= 0
        assert metrics.commits_analyzed > 0


def test_dora_metrics_analyzer_initialization(git_repo):
    """Test DORAMetricsAnalyzer initialization."""
    analyzer = DORAMetricsAnalyzer(git_repo)
    assert analyzer.repo_path == git_repo


def test_analyze_dora_metrics(git_repo):
    """Test DORA metrics analysis."""
    analyzer = DORAMetricsAnalyzer(git_repo)
    metrics = analyzer.analyze(period_days=30, branch="master")
    
    # Check metrics structure
    assert metrics.period
    assert metrics.date_range
    assert metrics.deployment_frequency
    assert metrics.deployment_frequency.deployments_count >= 0


def test_compare_dora_metrics(git_repo):
    """Test DORA metrics comparison."""
    analyzer = DORAMetricsAnalyzer(git_repo)
    
    now = datetime.now(UTC)
    before_end = now - timedelta(days=30)
    before_start = before_end - timedelta(days=30)
    after_start = now - timedelta(days=15)
    after_end = now
    
    before_metrics, after_metrics = analyzer.compare_periods(
        before_start, before_end,
        after_start, after_end,
        branch="master",
    )
    
    # Check that both metrics are present
    assert before_metrics
    assert after_metrics
    assert before_metrics.deployment_frequency
    assert after_metrics.deployment_frequency
