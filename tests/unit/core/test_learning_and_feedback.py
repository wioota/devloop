"""Tests for learning, feedback, and custom agent features."""

import asyncio
import pytest
from pathlib import Path
import tempfile

from devloop.core.custom_agent import (
    AgentBuilder,
    CustomAgentStore,
    CustomAgentType,
    PatternMatcherAgent,
    FileProcessorAgent,
    OutputAnalyzerAgent,
)
from devloop.core.learning import LearningSystem, AdaptiveAgentConfig
from devloop.core.feedback import FeedbackStore, FeedbackType, Feedback
from devloop.core.performance import PerformanceMonitor, PerformanceOptimizer


class TestCustomAgentBuilder:
    """Tests for custom agent builder."""

    def test_builder_minimal(self):
        """Test building agent with minimal config."""
        builder = AgentBuilder("test_agent", CustomAgentType.PATTERN_MATCHER)
        config = builder.build()

        assert config.name == "test_agent"
        assert config.agent_type == CustomAgentType.PATTERN_MATCHER
        assert config.id is not None
        assert config.enabled is True
        assert config.triggers == []

    def test_builder_with_description(self):
        """Test builder with description."""
        builder = AgentBuilder("test", CustomAgentType.FILE_PROCESSOR)
        builder.with_description("Test description")
        config = builder.build()

        assert config.description == "Test description"

    def test_builder_with_triggers(self):
        """Test builder with triggers."""
        builder = AgentBuilder("test", CustomAgentType.PATTERN_MATCHER)
        builder.with_triggers("file:created", "file:modified")
        config = builder.build()

        assert "file:created" in config.triggers
        assert "file:modified" in config.triggers

    def test_builder_with_config(self):
        """Test builder with configuration."""
        builder = AgentBuilder("test", CustomAgentType.OUTPUT_ANALYZER)
        builder.with_config(timeout=30, max_retries=3)
        config = builder.build()

        assert config.config["timeout"] == 30
        assert config.config["max_retries"] == 3

    def test_builder_chain(self):
        """Test builder method chaining."""
        config = (
            AgentBuilder("test", CustomAgentType.PATTERN_MATCHER)
            .with_description("Test agent")
            .with_triggers("file:created")
            .with_config(patterns=[r".*\.py$"])
            .with_metadata(version="1.0")
            .build()
        )

        assert config.name == "test"
        assert config.description == "Test agent"
        assert "file:created" in config.triggers
        assert config.config["patterns"] == [r".*\.py$"]
        assert config.metadata["version"] == "1.0"


class TestCustomAgentStore:
    """Tests for custom agent store."""

    @pytest.mark.asyncio
    async def test_save_and_load_agent(self):
        """Test saving and loading a custom agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CustomAgentStore(Path(tmpdir))

            config = AgentBuilder("test", CustomAgentType.PATTERN_MATCHER).build()
            await store.save_agent(config)

            loaded = await store.get_agent(config.id)
            assert loaded is not None
            assert loaded.name == "test"
            assert loaded.agent_type == CustomAgentType.PATTERN_MATCHER

    @pytest.mark.asyncio
    async def test_get_all_agents(self):
        """Test getting all agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CustomAgentStore(Path(tmpdir))

            config1 = AgentBuilder("agent1", CustomAgentType.PATTERN_MATCHER).build()
            config2 = AgentBuilder("agent2", CustomAgentType.FILE_PROCESSOR).build()

            await store.save_agent(config1)
            await store.save_agent(config2)

            agents = await store.get_all_agents()
            assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_delete_agent(self):
        """Test deleting an agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CustomAgentStore(Path(tmpdir))

            config = AgentBuilder("test", CustomAgentType.PATTERN_MATCHER).build()
            await store.save_agent(config)

            deleted = await store.delete_agent(config.id)
            assert deleted is True

            loaded = await store.get_agent(config.id)
            assert loaded is None

    @pytest.mark.asyncio
    async def test_list_agents_by_type(self):
        """Test filtering agents by type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CustomAgentStore(Path(tmpdir))

            config1 = AgentBuilder("agent1", CustomAgentType.PATTERN_MATCHER).build()
            config2 = AgentBuilder("agent2", CustomAgentType.FILE_PROCESSOR).build()
            config3 = AgentBuilder("agent3", CustomAgentType.PATTERN_MATCHER).build()

            await store.save_agent(config1)
            await store.save_agent(config2)
            await store.save_agent(config3)

            matchers = await store.list_agents_by_type(CustomAgentType.PATTERN_MATCHER)
            assert len(matchers) == 2


class TestPatternMatcherAgent:
    """Tests for pattern matcher agent."""

    @pytest.mark.asyncio
    async def test_pattern_matching(self):
        """Test pattern matching functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.txt"
            test_file.write_text(
                "hello world\nerror: something bad\nwarning: be careful"
            )

            config = (
                AgentBuilder("test", CustomAgentType.PATTERN_MATCHER)
                .with_config(patterns=[r"error:.*", r"warning:.*"])
                .build()
            )

            agent = PatternMatcherAgent(config)
            result = await agent.execute({"file_path": str(test_file)})

            assert "matches" in result
            assert len(result["matches"]) >= 2

    @pytest.mark.asyncio
    async def test_pattern_matching_no_file(self):
        """Test pattern matching with non-existent file."""
        config = AgentBuilder("test", CustomAgentType.PATTERN_MATCHER).build()
        agent = PatternMatcherAgent(config)

        result = await agent.execute({"file_path": "/nonexistent/file.txt"})
        assert "matches" in result
        assert result["matches"] == []


class TestFileProcessorAgent:
    """Tests for file processor agent."""

    @pytest.mark.asyncio
    async def test_file_read(self):
        """Test file reading operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.txt"
            test_file.write_text("line1\nline2\nline3")

            config = (
                AgentBuilder("test", CustomAgentType.FILE_PROCESSOR)
                .with_config(operation="read")
                .build()
            )

            agent = FileProcessorAgent(config)
            result = await agent.execute({"file_path": str(test_file)})

            assert result["status"] == "success"
            assert result["operation"] == "read"
            assert result["lines"] == 3

    @pytest.mark.asyncio
    async def test_file_analyze(self):
        """Test file analysis operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            test_file = tmpdir / "test.py"
            content = "def hello():\n    pass\n\n# comment\n"
            test_file.write_text(content)

            config = (
                AgentBuilder("test", CustomAgentType.FILE_PROCESSOR)
                .with_config(operation="analyze")
                .build()
            )

            agent = FileProcessorAgent(config)
            result = await agent.execute({"file_path": str(test_file)})

            assert result["status"] == "success"
            assert result["operation"] == "analyze"
            assert result["total_lines"] > 0


class TestOutputAnalyzerAgent:
    """Tests for output analyzer agent."""

    @pytest.mark.asyncio
    async def test_output_analysis(self):
        """Test output analysis."""
        config = (
            AgentBuilder("test", CustomAgentType.OUTPUT_ANALYZER)
            .with_config(error_patterns=[r"Error:.*"])
            .build()
        )

        agent = OutputAnalyzerAgent(config)
        output = "Processing...\nError: something failed\nError: another issue"

        result = await agent.execute({"output": output})

        assert "output_length" in result
        assert "line_count" in result
        assert "errors_found" in result


class TestLearningSystem:
    """Tests for learning system."""

    @pytest.mark.asyncio
    async def test_learn_pattern(self):
        """Test learning a behavior pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learning = LearningSystem(Path(tmpdir))

            await learning.learn_pattern(
                agent_name="linter",
                pattern_name="style_error",
                description="PEP 8 style violation",
                conditions={"file_type": "python"},
                recommended_action="auto_fix",
                confidence=0.8,
            )

            patterns = await learning.get_patterns_for_agent("linter")
            assert len(patterns) > 0

    @pytest.mark.asyncio
    async def test_get_recommendations(self):
        """Test getting recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learning = LearningSystem(Path(tmpdir))

            await learning.learn_pattern(
                agent_name="linter",
                pattern_name="style_error",
                description="PEP 8 style violation",
                conditions={"file_type": "python"},
                recommended_action="auto_fix",
                confidence=0.9,
            )

            recommendations = await learning.get_recommendations("linter")
            assert len(recommendations) > 0
            assert recommendations[0]["confidence"] >= 0.7

    @pytest.mark.asyncio
    async def test_store_insight(self):
        """Test storing insights."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learning = LearningSystem(Path(tmpdir))

            await learning.store_insight(
                agent_name="formatter",
                insight_type="slow_execution",
                data={"duration": 5.0},
            )

            insights = await learning.get_insights_for_agent("formatter")
            assert "slow_execution" in insights

    @pytest.mark.asyncio
    async def test_suggest_optimization(self):
        """Test suggesting optimizations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learning = LearningSystem(Path(tmpdir))

            await learning.store_insight(
                agent_name="formatter",
                insight_type="slow_execution",
                data={"duration": 5.0},
            )

            suggestion = await learning.suggest_optimization("formatter")
            assert suggestion is not None


class TestAdaptiveAgentConfig:
    """Tests for adaptive agent configuration."""

    @pytest.mark.asyncio
    async def test_get_optimal_parameters(self):
        """Test getting optimal parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learning = LearningSystem(Path(tmpdir))
            adaptive = AdaptiveAgentConfig(learning, "test_agent")

            params = await adaptive.get_optimal_parameters()

            assert "debounce_seconds" in params
            assert "timeout_seconds" in params
            assert "retry_count" in params
            assert "batch_size" in params

    @pytest.mark.asyncio
    async def test_should_execute(self):
        """Test execution decision logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            learning = LearningSystem(Path(tmpdir))
            adaptive = AdaptiveAgentConfig(learning, "test_agent")

            should_run = await adaptive.should_execute()
            assert should_run is True


class TestFeedbackAndPerformance:
    """Tests for feedback and performance integration."""

    @pytest.mark.asyncio
    async def test_feedback_storage(self):
        """Test storing feedback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FeedbackStore(Path(tmpdir))

            feedback = Feedback(
                id="test_1",
                agent_name="linter",
                event_type="file:modified",
                feedback_type=FeedbackType.THUMBS_UP,
                value=True,
            )

            await store.store_feedback(feedback)
            items = await store.get_feedback_for_agent("linter")

            assert len(items) > 0

    @pytest.mark.asyncio
    async def test_performance_monitoring(self):
        """Test performance monitoring."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(Path(tmpdir))

            async with monitor.monitor_operation("test_operation") as metrics:
                await asyncio.sleep(0.01)
                assert metrics.operation_name == "test_operation"

    @pytest.mark.asyncio
    async def test_performance_optimizer(self):
        """Test performance optimizer with debounce logic."""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = PerformanceMonitor(Path(tmpdir))
            optimizer = PerformanceOptimizer(monitor)

            # Mock time to avoid flaky timing-based tests
            mock_time_values = [
                100.0,
                100.0,
                102.0,
            ]  # First two calls at same time, third at +2 seconds

            with patch("devloop.core.performance.time.time") as mock_time:
                mock_time.side_effect = mock_time_values

                # Test debouncing
                skip1 = await optimizer.should_skip_operation("test_op", 1.0)
                assert skip1 is False, "First call should not skip"

                skip2 = await optimizer.should_skip_operation("test_op", 1.0)
                assert skip2 is True, "Second call within debounce window should skip"

                skip3 = await optimizer.should_skip_operation("test_op", 1.0)
                assert skip3 is False, "Call after debounce window should not skip"
