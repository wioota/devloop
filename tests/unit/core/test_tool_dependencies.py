"""Tests for tool dependency management."""

from devloop.core.tool_dependencies import ToolDependencyManager


class TestToolDetection:
    """Test tool availability detection."""

    def test_check_python_available(self):
        """Python should always be available."""
        assert ToolDependencyManager.check_tool_available("python")

    def test_check_git_available(self):
        """Git should be available in test environment."""
        assert ToolDependencyManager.check_tool_available("git")

    def test_check_missing_tool(self):
        """Missing tools should return False."""
        assert not ToolDependencyManager.check_tool_available("nonexistent-tool-xyz")

    def test_check_tool_with_custom_command(self):
        """Should handle custom commands."""
        # Python module command
        assert ToolDependencyManager.check_tool_available("pytest", "python -m pytest")


class TestVersionDetection:
    """Test version detection."""

    def test_get_python_version(self):
        """Should detect Python version."""
        version = ToolDependencyManager.get_tool_version("python")
        assert version is not None
        assert "." in version  # Should have format x.y.z

    def test_get_git_version(self):
        """Should detect Git version."""
        version = ToolDependencyManager.get_tool_version("git")
        assert version is not None

    def test_get_missing_tool_version(self):
        """Missing tools should return None."""
        version = ToolDependencyManager.get_tool_version("nonexistent-tool-xyz")
        assert version is None

    def test_parse_version(self):
        """Should parse version strings correctly."""
        assert ToolDependencyManager.parse_version("3.11.0") == (3, 11, 0)
        assert ToolDependencyManager.parse_version("1.2.3") == (1, 2, 3)
        assert ToolDependencyManager.parse_version("2.0.0") == (2, 0, 0)
        assert ToolDependencyManager.parse_version(None) == (0, 0, 0)
        assert ToolDependencyManager.parse_version("invalid") == (0, 0, 0)


class TestCompatibilityCheck:
    """Test version compatibility checks."""

    def test_check_python_compatibility(self):
        """Python should be compatible."""
        compatible, version = ToolDependencyManager.check_version_compatibility(
            "python"
        )
        assert compatible
        assert version is not None

    def test_check_git_compatibility(self):
        """Git should be compatible."""
        compatible, version = ToolDependencyManager.check_version_compatibility("git")
        assert compatible

    def test_missing_tool_incompatibility(self):
        """Missing tools should be incompatible."""
        compatible, version = ToolDependencyManager.check_version_compatibility(
            "nonexistent-tool"
        )
        assert not compatible
        assert version is None

    def test_check_all_tools(self):
        """Should return status for all tools."""
        results = ToolDependencyManager.check_all_tools()
        assert isinstance(results, dict)
        assert len(results) > 0

        # Check structure
        for tool_name, info in results.items():
            assert "available" in info
            assert "version" in info
            assert "compatible" in info
            assert "critical" in info
            assert "category" in info

    def test_critical_tools_available(self):
        """All critical Python tools should be available."""
        results = ToolDependencyManager.check_all_tools()

        critical_python_tools = ["ruff", "black", "mypy", "pytest", "python", "git"]
        for tool in critical_python_tools:
            assert results[tool]["available"], f"{tool} should be available"
            assert results[tool]["compatible"], f"{tool} should be compatible"


class TestToolInfo:
    """Test tool information retrieval."""

    def test_get_tool_info_python(self):
        """Should retrieve Python tool info."""
        tool = ToolDependencyManager._get_tool_info("python")
        assert tool is not None
        assert tool.name == "python"
        assert tool.min_version == "3.11.0"
        assert tool.critical

    def test_get_tool_info_optional(self):
        """Should retrieve optional tool info."""
        tool = ToolDependencyManager._get_tool_info("snyk")
        assert tool is not None
        assert tool.name == "snyk"
        assert not tool.critical

    def test_get_nonexistent_tool_info(self):
        """Should return None for nonexistent tools."""
        tool = ToolDependencyManager._get_tool_info("nonexistent-tool")
        assert tool is None


class TestStartupCheck:
    """Test startup health checks."""

    def test_startup_check_passes(self):
        """Startup check should pass when critical tools available."""
        result = ToolDependencyManager.startup_check(fail_on_missing_critical=False)
        assert result is True

    def test_get_python_tools(self):
        """Should access Python tools dictionary."""
        assert "ruff" in ToolDependencyManager.PYTHON_TOOLS
        assert "black" in ToolDependencyManager.PYTHON_TOOLS
        assert "mypy" in ToolDependencyManager.PYTHON_TOOLS

    def test_get_external_tools(self):
        """Should access external tools dictionary."""
        assert "git" in ToolDependencyManager.EXTERNAL_TOOLS
        assert "python" in ToolDependencyManager.EXTERNAL_TOOLS

    def test_get_optional_tools(self):
        """Should access optional tools dictionary."""
        assert "snyk" in ToolDependencyManager.OPTIONAL_TOOLS
        assert "eslint" in ToolDependencyManager.OPTIONAL_TOOLS


class TestToolInfoDataclass:
    """Test ToolInfo dataclass."""

    def test_tool_info_defaults(self):
        """ToolInfo should have proper defaults."""
        from devloop.core.tool_dependencies import ToolInfo

        tool = ToolInfo(name="test", description="Test tool")
        assert tool.command == "test"
        assert tool.version_flag == "--version"
        assert not tool.critical

    def test_tool_info_custom_command(self):
        """ToolInfo should support custom commands."""
        from devloop.core.tool_dependencies import ToolInfo

        tool = ToolInfo(
            name="pytest", description="Test runner", command="python -m pytest"
        )
        assert tool.command == "python -m pytest"
