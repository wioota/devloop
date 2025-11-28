#!/usr/bin/env python3
"""Git Commit Message Assistant - Generates conventional commit messages."""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..core.agent import Agent, AgentResult
from ..core.context_store import context_store, Finding
from ..core.event import Event


@dataclass
class CommitConfig:
    """Configuration for commit message generation."""

    conventional_commits: bool = True
    max_message_length: int = 72
    include_breaking_changes: bool = True
    analyze_file_changes: bool = True
    auto_generate_scope: bool = True
    common_types: Optional[List[str]] = None

    def __post_init__(self):
        if self.common_types is None:
            self.common_types = [
                "feat",
                "fix",
                "docs",
                "style",
                "refactor",
                "test",
                "chore",
                "perf",
                "ci",
                "build",
            ]


class CommitSuggestion:
    """Commit message suggestion."""

    def __init__(
        self,
        message: str,
        confidence: float,
        reasoning: str,
        alternatives: List[str] = None,
    ):
        self.message = message
        self.confidence = confidence
        self.reasoning = reasoning
        self.alternatives = alternatives or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
        }


class GitCommitAssistantAgent(Agent):
    """Agent for generating conventional commit messages."""

    def __init__(self, config: Dict[str, Any], event_bus):
        super().__init__(
            "git-commit-assistant", ["git:pre-commit", "git:commit"], event_bus
        )
        self.config = CommitConfig(**config)

    async def handle(self, event: Event) -> AgentResult:
        """Handle git events by suggesting commit messages."""

        event_type = event.type

        if event_type == "git:pre-commit":
            # Analyze staged changes and suggest commit message
            return await self._handle_pre_commit(event)
        elif event_type == "git:commit":
            # Could validate commit message format
            return await self._handle_commit(event)
        else:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"Unsupported event type: {event_type}",
            )

    async def _handle_pre_commit(self, event: Event) -> AgentResult:
        """Generate commit message suggestions for staged changes."""
        try:
            # Get staged files
            staged_files = await self._get_staged_files()
            if not staged_files:
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    duration=0.0,
                    message="No staged files to analyze",
                )

            # Analyze changes
            change_analysis = await self._analyze_changes(staged_files)

            # Generate commit suggestions
            suggestions = self._generate_commit_suggestions(change_analysis)

            agent_result = AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,
                message=f"Generated {len(suggestions)} commit message suggestions",
                data={
                    "staged_files": staged_files,
                    "change_analysis": change_analysis,
                    "suggestions": [s.to_dict() for s in suggestions],
                    "top_suggestion": suggestions[0].to_dict() if suggestions else None,
                },
            )

            # Write to context store for Claude Code integration
            if suggestions:
                top_suggestion = suggestions[0]
                await context_store.add_finding(
                    Finding(
                        id=f"{self.name}-suggestion",
                        agent=self.name,
                        timestamp=str(event.timestamp),
                        file="",
                        message=f"Suggested commit message: {top_suggestion.message}",
                        suggestion=top_suggestion.message,
                        context=top_suggestion.to_dict(),
                    )
                )

            return agent_result

        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"Failed to generate commit suggestions: {str(e)}",
            )

    async def _handle_commit(self, event: Event) -> AgentResult:
        """Validate commit message format."""
        commit_msg = event.payload.get("message", "")
        if not commit_msg:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message="No commit message to validate",
            )

        is_valid, feedback = self._validate_commit_message(commit_msg)

        return AgentResult(
            agent_name=self.name,
            success=is_valid,
            duration=0.0,
            message=f"Commit message validation: {'valid' if is_valid else 'invalid'}",
            data={"message": commit_msg, "is_valid": is_valid, "feedback": feedback},
        )

    async def _get_staged_files(self) -> List[str]:
        """Get list of staged files."""
        try:
            result = await asyncio.create_subprocess_exec(
                "git",
                "diff",
                "--cached",
                "--name-only",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode == 0:
                files = stdout.decode().strip().split("\n")
                return [f for f in files if f.strip()]
            return []

        except Exception:
            return []

    async def _analyze_changes(self, files: List[str]) -> Dict[str, Any]:
        """Analyze the changes in staged files."""
        analysis: Dict[str, Any] = {
            "files_changed": len(files),
            "file_types": {},
            "change_types": [],
            "affected_modules": set(),
            "breaking_changes": False,
        }

        # Categorize files by type
        for file in files:
            path = Path(file)
            ext = path.suffix

            file_types = analysis["file_types"]
            if ext == ".py":
                file_types["python"] = file_types.get("python", 0) + 1
            elif ext in [".js", ".ts", ".jsx", ".tsx"]:
                file_types["javascript"] = file_types.get("javascript", 0) + 1
            elif ext in [".md", ".rst", ".txt"]:
                file_types["documentation"] = file_types.get("documentation", 0) + 1
            elif ext in [".yml", ".yaml", ".json", ".toml"]:
                file_types["config"] = file_types.get("config", 0) + 1
            elif ext in [".sh", ".bat", ".ps1"]:
                file_types["scripts"] = file_types.get("scripts", 0) + 1
            else:
                file_types["other"] = file_types.get("other", 0) + 1

            # Extract module/area from path
            parts = path.parts
            if len(parts) > 1:
                module = parts[0] if len(parts) > 1 else "root"
                analysis["affected_modules"].add(module)

        # Determine change types based on files
        change_types = analysis["change_types"]
        if analysis["file_types"].get("documentation", 0) > 0:
            change_types.append("docs")
        if analysis["file_types"].get("config", 0) > 0:
            change_types.append("ci")
        if analysis["file_types"].get("scripts", 0) > 0:
            change_types.append("ci")

        # Try to determine primary change type
        if "test_" in " ".join(files).lower() or "spec" in " ".join(files).lower():
            change_types.append("test")
        elif any("fix" in f.lower() or "bug" in f.lower() for f in files):
            change_types.append("fix")
        elif any("feature" in f.lower() or "feat" in f.lower() for f in files):
            change_types.append("feat")
        else:
            change_types.append("refactor")  # Default assumption

        analysis["affected_modules"] = list(analysis["affected_modules"])

        return analysis

    def _generate_commit_suggestions(
        self, analysis: Dict[str, Any]
    ) -> List[CommitSuggestion]:
        """Generate commit message suggestions based on analysis."""
        suggestions = []

        # Determine primary type
        primary_type = self._determine_primary_type(analysis)

        # Generate scope
        scope = self._generate_scope(analysis)

        # Create main suggestion
        message = f"{primary_type}"
        if scope:
            message += f"({scope})"

        message += ": "

        # Add description based on analysis
        description = self._generate_description(analysis, primary_type)
        message += description

        # Ensure message length
        if len(message) > self.config.max_message_length:
            message = message[: self.config.max_message_length - 3] + "..."

        suggestions.append(
            CommitSuggestion(
                message=message,
                confidence=0.8,
                reasoning=f"Based on {analysis['files_changed']} files changed, primarily {primary_type} changes",
            )
        )

        # Generate alternative suggestions
        alternatives = self._generate_alternatives(primary_type, scope, analysis)
        suggestions.extend(alternatives)

        return suggestions

    def _determine_primary_type(self, analysis: Dict[str, Any]) -> str:
        """Determine the primary commit type."""
        change_types = analysis.get("change_types", [])

        # Priority order for commit types
        type_priority = {
            "fix": ["fix", "bug", "patch"],
            "feat": ["feat", "feature", "add"],
            "docs": ["docs", "documentation"],
            "test": ["test", "spec"],
            "ci": ["ci", "config", "build"],
            "refactor": ["refactor", "clean", "improve"],
            "style": ["style", "format"],
            "perf": ["perf", "performance", "optimize"],
            "chore": ["chore", "maintenance"],
        }

        for commit_type, keywords in type_priority.items():
            for change_type in change_types:
                if any(keyword in change_type.lower() for keyword in keywords):
                    return commit_type

        # Default to refactor if nothing specific
        return "refactor"

    def _generate_scope(self, analysis: Dict[str, Any]) -> str:
        """Generate scope for conventional commit."""
        if not self.config.auto_generate_scope:
            return ""

        modules = analysis.get("affected_modules", [])
        if len(modules) == 1:
            return modules[0].lower().replace(" ", "-")
        elif len(modules) > 1:
            # Find common prefix
            common = ""
            for i, char in enumerate(modules[0]):
                if all(
                    module.startswith(modules[0][: i + 1]) for module in modules[1:]
                ):
                    common = modules[0][: i + 1]
                else:
                    break
            return common.lower().replace(" ", "-") if common else ""

        return ""

    def _generate_description(self, analysis: Dict[str, Any], primary_type: str) -> str:
        """Generate commit description."""
        files_changed = analysis.get("files_changed", 0)

        if primary_type == "docs":
            return f"update documentation ({files_changed} files)"
        elif primary_type == "test":
            return f"add/update tests ({files_changed} files)"
        elif primary_type == "ci":
            return f"update CI/configuration ({files_changed} files)"
        elif primary_type == "fix":
            return f"fix issues in {files_changed} files"
        elif primary_type == "feat":
            return f"add new features ({files_changed} files)"
        elif primary_type == "refactor":
            return f"refactor code ({files_changed} files)"
        elif primary_type == "style":
            return f"improve code style ({files_changed} files)"
        elif primary_type == "perf":
            return f"improve performance ({files_changed} files)"
        else:
            return f"update {files_changed} files"

    def _generate_alternatives(
        self, primary_type: str, scope: str, analysis: Dict[str, Any]
    ) -> List[CommitSuggestion]:
        """Generate alternative commit message suggestions."""
        alternatives = []

        # Alternative with different wording
        alt1 = f"{primary_type}"
        if scope:
            alt1 += f"({scope})"
        alt1 += ": update code"

        alternatives.append(
            CommitSuggestion(
                message=alt1, confidence=0.6, reasoning="Simple alternative message"
            )
        )

        # Alternative without scope
        alt2 = f"{primary_type}: {self._generate_description(analysis, primary_type)}"

        alternatives.append(
            CommitSuggestion(
                message=alt2, confidence=0.5, reasoning="Message without scope"
            )
        )

        return alternatives

    def _validate_commit_message(self, message: str) -> tuple[bool, str]:
        """Validate commit message format."""
        if not self.config.conventional_commits:
            return True, "Conventional commits not enforced"

        # Basic conventional commit validation
        if ":" not in message:
            return False, "Missing ':' separator for conventional commit format"

        type_part = message.split(":")[0].strip()

        # Check if type is valid
        if "(" in type_part and ")" in type_part:
            # Has scope
            type_only = type_part.split("(")[0]
        else:
            type_only = type_part

        if self.config.common_types and type_only not in self.config.common_types:
            return (
                False,
                f"Unknown commit type '{type_only}'. Use one of: {', '.join(self.config.common_types)}",
            )

        # Check length
        if len(message) > 100:  # Allow longer than subject line for full message
            return (
                False,
                "Commit message too long (keep under 100 characters for subject)",
            )

        return True, "Valid conventional commit format"
