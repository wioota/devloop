"""Custom agent creation framework for Phase 3."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiofiles


class CustomAgentType(Enum):
    """Types of custom agents that can be created."""

    PATTERN_MATCHER = "pattern_matcher"
    FILE_PROCESSOR = "file_processor"
    OUTPUT_ANALYZER = "output_analyzer"
    COMPOSITE = "composite"


@dataclass
class CustomAgentConfig:
    """Configuration for a custom agent."""

    id: str
    name: str
    description: str
    agent_type: CustomAgentType
    enabled: bool = True
    triggers: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


class AgentBuilder:
    """Builder for creating custom agents programmatically."""

    def __init__(self, name: str, agent_type: CustomAgentType):
        """Initialize agent builder.

        Args:
            name: Name of the custom agent
            agent_type: Type of custom agent
        """
        self.name = name
        self.agent_type = agent_type
        self.description = ""
        self.triggers: List[str] = []
        self.config: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

    def with_description(self, description: str) -> AgentBuilder:
        """Add description."""
        self.description = description
        return self

    def with_triggers(self, *triggers: str) -> AgentBuilder:
        """Add event triggers."""
        self.triggers.extend(triggers)
        return self

    def with_config(self, **config_items) -> AgentBuilder:
        """Add configuration items."""
        self.config.update(config_items)
        return self

    def with_metadata(self, **metadata_items) -> AgentBuilder:
        """Add metadata."""
        self.metadata.update(metadata_items)
        return self

    def build(self) -> CustomAgentConfig:
        """Build the custom agent configuration."""
        return CustomAgentConfig(
            id=str(uuid4()),
            name=self.name,
            description=self.description,
            agent_type=self.agent_type,
            triggers=self.triggers,
            config=self.config,
            metadata=self.metadata,
        )


class CustomAgentStore:
    """Storage for custom agent definitions."""

    def __init__(self, storage_path: Path):
        """Initialize custom agent store.

        Args:
            storage_path: Path to store custom agent definitions
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.agents_file = storage_path / "agents.json"

    async def save_agent(self, config: CustomAgentConfig) -> None:
        """Save a custom agent configuration.

        Args:
            config: Agent configuration to save
        """
        agents = await self._load_all_agents()

        # Update or add
        agents[config.id] = {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "agent_type": config.agent_type.value,
            "enabled": config.enabled,
            "triggers": config.triggers,
            "config": config.config,
            "metadata": config.metadata,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

        async with aiofiles.open(self.agents_file, "w") as f:
            await f.write(json.dumps(agents, indent=2))

    async def get_agent(self, agent_id: str) -> Optional[CustomAgentConfig]:
        """Get a custom agent by ID.

        Args:
            agent_id: Agent ID to retrieve

        Returns:
            Agent configuration or None if not found
        """
        agents = await self._load_all_agents()

        if agent_id not in agents:
            return None

        data = agents[agent_id]
        return CustomAgentConfig(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            agent_type=CustomAgentType(data["agent_type"]),
            enabled=data.get("enabled", True),
            triggers=data.get("triggers", []),
            config=data.get("config", {}),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def get_all_agents(self) -> List[CustomAgentConfig]:
        """Get all custom agents.

        Returns:
            List of all custom agent configurations
        """
        agents_data = await self._load_all_agents()
        agents = []

        for data in agents_data.values():
            agents.append(
                CustomAgentConfig(
                    id=data["id"],
                    name=data["name"],
                    description=data["description"],
                    agent_type=CustomAgentType(data["agent_type"]),
                    enabled=data.get("enabled", True),
                    triggers=data.get("triggers", []),
                    config=data.get("config", {}),
                    metadata=data.get("metadata", {}),
                    created_at=data.get("created_at"),
                    updated_at=data.get("updated_at"),
                )
            )

        return agents

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete a custom agent.

        Args:
            agent_id: Agent ID to delete

        Returns:
            True if deleted, False if not found
        """
        agents = await self._load_all_agents()

        if agent_id not in agents:
            return False

        del agents[agent_id]

        async with aiofiles.open(self.agents_file, "w") as f:
            await f.write(json.dumps(agents, indent=2))

        return True

    async def list_agents_by_type(
        self, agent_type: CustomAgentType
    ) -> List[CustomAgentConfig]:
        """Get agents by type.

        Args:
            agent_type: Type of agents to retrieve

        Returns:
            List of agents matching the type
        """
        agents_data = await self._load_all_agents()
        agents = []

        for data in agents_data.values():
            if CustomAgentType(data["agent_type"]) == agent_type:
                agents.append(
                    CustomAgentConfig(
                        id=data["id"],
                        name=data["name"],
                        description=data["description"],
                        agent_type=agent_type,
                        enabled=data.get("enabled", True),
                        triggers=data.get("triggers", []),
                        config=data.get("config", {}),
                        metadata=data.get("metadata", {}),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                    )
                )

        return agents

    async def _load_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Load all agents from file.

        Returns:
            Dictionary of agents indexed by ID
        """
        if not self.agents_file.exists():
            return {}

        async with aiofiles.open(self.agents_file, "r") as f:
            content = await f.read()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}


class AgentTemplate(ABC):
    """Base template for creating custom agents."""

    def __init__(self, config: CustomAgentConfig):
        """Initialize agent template.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.id = config.id
        self.name = config.name
        self.agent_type = config.agent_type

    @abstractmethod
    async def execute(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the custom agent.

        Args:
            event_data: Event data to process

        Returns:
            Result of agent execution
        """
        pass

    async def should_handle(self, event_type: str) -> bool:
        """Check if this agent should handle the event.

        Args:
            event_type: Type of event

        Returns:
            True if agent should handle the event
        """
        if not self.config.enabled:
            return False

        return event_type in self.config.triggers


class PatternMatcherAgent(AgentTemplate):
    """Custom agent that matches patterns in files."""

    async def execute(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pattern matching.

        Args:
            event_data: Event data containing file information

        Returns:
            Matches found in files
        """
        patterns = self.config.config.get("patterns", [])
        file_path = event_data.get("file_path", "")

        if not file_path or not patterns:
            return {"matches": []}

        matches = []
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                content = path.read_text()

                import re

                for pattern in patterns:
                    regex = re.compile(pattern)
                    for match in regex.finditer(content):
                        matches.append(
                            {
                                "pattern": pattern,
                                "match": match.group(),
                                "position": match.start(),
                            }
                        )
        except Exception as e:
            return {"error": str(e), "matches": []}

        return {"matches": matches}


class FileProcessorAgent(AgentTemplate):
    """Custom agent that processes files."""

    async def execute(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file processing.

        Args:
            event_data: Event data containing file information

        Returns:
            Processing results
        """
        file_path = event_data.get("file_path", "")
        operation = self.config.config.get("operation", "read")

        try:
            path = Path(file_path)

            if operation == "read" and path.exists():
                content = path.read_text()
                return {
                    "status": "success",
                    "operation": "read",
                    "file_size": len(content),
                    "lines": len(content.splitlines()),
                }
            elif operation == "analyze" and path.exists():
                content = path.read_text()
                lines = content.splitlines()
                return {
                    "status": "success",
                    "operation": "analyze",
                    "total_lines": len(lines),
                    "empty_lines": len([line for line in lines if not line.strip()]),
                    "comment_lines": len(
                        [line for line in lines if line.strip().startswith("#")]
                    ),
                }
            else:
                return {"status": "error", "message": f"File not found: {file_path}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}


class OutputAnalyzerAgent(AgentTemplate):
    """Custom agent that analyzes command output."""

    async def execute(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze output.

        Args:
            event_data: Event data containing output information

        Returns:
            Analysis results
        """
        output = event_data.get("output", "")
        patterns = self.config.config.get("error_patterns", [])

        analysis = {
            "output_length": len(output),
            "line_count": len(output.splitlines()),
            "errors_found": 0,
            "warnings_found": 0,
        }

        if patterns:
            import re

            for pattern in patterns:
                regex = re.compile(pattern)
                matches = regex.findall(output)
                if matches:
                    analysis["errors_found"] += len(matches)

        # Simple heuristic analysis
        lower_output = output.lower()
        analysis["warnings_found"] = lower_output.count("warning")
        analysis["errors_found"] += lower_output.count("error")

        return analysis


def get_agent_template(config: CustomAgentConfig) -> AgentTemplate:
    """Get the appropriate template instance for a custom agent.

    Args:
        config: Agent configuration

    Returns:
        Agent template instance
    """
    if config.agent_type == CustomAgentType.PATTERN_MATCHER:
        return PatternMatcherAgent(config)
    elif config.agent_type == CustomAgentType.FILE_PROCESSOR:
        return FileProcessorAgent(config)
    elif config.agent_type == CustomAgentType.OUTPUT_ANALYZER:
        return OutputAnalyzerAgent(config)
    else:
        raise ValueError(f"Unsupported agent type: {config.agent_type}")
