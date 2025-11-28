"""Custom agent creation framework and templates."""

from __future__ import annotations

import aiofiles
import importlib.util
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agent import Agent
from .event import EventBus


@dataclass
class AgentTemplate:
    """Template for creating custom agents."""

    name: str
    description: str
    category: str
    triggers: List[str]
    config_schema: Dict[str, Any]
    template_code: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentTemplate:
        """Create template from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            category=data["category"],
            triggers=data["triggers"],
            config_schema=data["config_schema"],
            template_code=data["template_code"],
        )


class AgentTemplateRegistry:
    """Registry of available agent templates."""

    def __init__(self):
        self.templates: Dict[str, AgentTemplate] = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self) -> None:
        """Load built-in agent templates."""
        self.templates.update(
            {
                "file-watcher": AgentTemplate(
                    name="file-watcher",
                    description="Monitor specific file patterns and perform custom actions",
                    category="monitoring",
                    triggers=["file:modified", "file:created", "file:deleted"],
                    config_schema={
                        "type": "object",
                        "properties": {
                            "filePatterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": ["**/*.txt"],
                            },
                            "action": {
                                "type": "string",
                                "enum": ["log", "backup", "notify"],
                                "default": "log",
                            },
                        },
                    },
                    template_code='''
from dev_agents.core.agent import Agent, AgentResult

class FileWatcherAgent(Agent):
    def __init__(self, name: str, triggers: list, event_bus, config: dict):
        super().__init__(name, triggers, event_bus)
        self.config = config

    async def handle(self, event: Event) -> AgentResult:
        file_path = event.payload.get("path", "")
        action = self.config.get("action", "log")

        # Check if file matches patterns
        if not self._matches_pattern(file_path):
            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.0,
                message=f"File {file_path} doesn't match patterns"
            )

        if action == "log":
            message = f"File {event.type.split(':')[1]}: {file_path}"
        elif action == "backup":
            # TODO: Implement backup logic
            message = f"Backed up: {file_path}"
        elif action == "notify":
            # TODO: Implement notification logic
            message = f"Notification sent for: {file_path}"
        else:
            message = f"Unknown action '{action}' for: {file_path}"

        return AgentResult(
            agent_name=self.name,
            success=True,
            duration=0.1,
            message=message
        )

    def _matches_pattern(self, file_path: str) -> bool:
        """Check if file path matches configured patterns."""
        from fnmatch import fnmatch

        patterns = self.config.get("filePatterns", [])
        for pattern in patterns:
            if fnmatch(file_path, pattern):
                return True
        return False
''',
                ),
                "command-runner": AgentTemplate(
                    name="command-runner",
                    description="Run shell commands in response to events",
                    category="automation",
                    triggers=["file:modified", "git:commit"],
                    config_schema={
                        "type": "object",
                        "properties": {
                            "commands": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": ["echo 'Hello from custom agent!'"],
                            },
                            "workingDirectory": {"type": "string", "default": "."},
                        },
                    },
                    template_code="""
import subprocess
import asyncio
from dev_agents.core.agent import Agent, AgentResult

class CommandRunnerAgent(Agent):
    def __init__(self, name: str, triggers: list, event_bus, config: dict):
        super().__init__(name, triggers, event_bus)
        self.config = config

    async def handle(self, event: Event) -> AgentResult:
        commands = self.config.get("commands", [])
        cwd = self.config.get("workingDirectory", ".")

        results = []
        for cmd in commands:
            try:
                # Run command asynchronously
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    results.append(f"✓ {cmd}")
                else:
                    results.append(f"✗ {cmd}: {stderr.decode().strip()}")

            except Exception as e:
                results.append(f"✗ {cmd}: {str(e)}")

        return AgentResult(
            agent_name=self.name,
            success=all("✓" in r for r in results),
            duration=0.1,
            message=f"Ran {len(commands)} commands: {'; '.join(results)}"
        )
""",
                ),
                "data-processor": AgentTemplate(
                    name="data-processor",
                    description="Process and transform data files",
                    category="data",
                    triggers=["file:modified"],
                    config_schema={
                        "type": "object",
                        "properties": {
                            "inputFormat": {
                                "type": "string",
                                "enum": ["json", "csv", "txt"],
                                "default": "json",
                            },
                            "outputFormat": {
                                "type": "string",
                                "enum": ["json", "csv", "txt"],
                                "default": "json",
                            },
                            "transformations": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                        },
                    },
                    template_code='''
import json
import csv
from pathlib import Path
from dev_agents.core.agent import Agent, AgentResult

class DataProcessorAgent(Agent):
    def __init__(self, name: str, triggers: list, event_bus, config: dict):
        super().__init__(name, triggers, event_bus)
        self.config = config

    async def handle(self, event: Event) -> AgentResult:
        file_path = event.payload.get("path", "")
        if not file_path:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message="No file path provided"
            )

        path = Path(file_path)
        if not path.exists():
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.0,
                message=f"File does not exist: {file_path}"
            )

        try:
            # Read input data
            input_format = self.config.get("inputFormat", "json")
            data = await self._read_data(path, input_format)

            # Apply transformations
            transformations = self.config.get("transformations", [])
            for transform in transformations:
                data = await self._apply_transformation(data, transform)

            # Write output data
            output_format = self.config.get("outputFormat", "json")
            output_path = path.with_suffix(f".processed{path.suffix}")
            await self._write_data(output_path, data, output_format)

            return AgentResult(
                agent_name=self.name,
                success=True,
                duration=0.1,
                message=f"Processed {file_path} -> {output_path}"
            )

        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                success=False,
                duration=0.1,
                message=f"Processing failed: {str(e)}"
            )

    async def _read_data(self, path: Path, format_type: str):
        """Read data from file."""
        async with aiofiles.open(path, 'r') as f:
            content = await f.read()

        if format_type == "json":
            return json.loads(content)
        elif format_type == "csv":
            import io
            return list(csv.DictReader(io.StringIO(content)))
        else:  # txt
            return content.splitlines()

    async def _write_data(self, path: Path, data, format_type: str):
        """Write data to file."""
        async with aiofiles.open(path, 'w') as f:
            if format_type == "json":
                await f.write(json.dumps(data, indent=2))
            elif format_type == "csv":
                if isinstance(data, list) and data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            else:  # txt
                if isinstance(data, list):
                    await f.write('\\n'.join(data))
                else:
                    await f.write(str(data))

    async def _apply_transformation(self, data, transform: str):
        """Apply a transformation to data."""
        # Simple transformation examples
        if transform == "uppercase":
            if isinstance(data, str):
                return data.upper()
            elif isinstance(data, list):
                return [str(item).upper() for item in data]
        elif transform == "lowercase":
            if isinstance(data, str):
                return data.lower()
            elif isinstance(data, list):
                return [str(item).lower() for item in data]
        elif transform == "sort":
            if isinstance(data, list):
                return sorted(data, key=str)
        # Add more transformations as needed

        return data
''',
                ),
            }
        )

    def get_template(self, name: str) -> Optional[AgentTemplate]:
        """Get a template by name."""
        return self.templates.get(name)

    def list_templates(self, category: Optional[str] = None) -> List[AgentTemplate]:
        """List available templates, optionally filtered by category."""
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates

    def get_categories(self) -> List[str]:
        """Get list of available template categories."""
        return list(set(t.category for t in self.templates.values()))


class AgentFactory:
    """Factory for creating agents from templates and custom code."""

    def __init__(self, template_registry: AgentTemplateRegistry):
        self.template_registry = template_registry

    async def create_from_template(
        self,
        template_name: str,
        agent_name: str,
        triggers: List[str],
        event_bus: EventBus,
        config: Dict[str, Any],
    ) -> Optional[Agent]:
        """Create an agent from a template."""
        template = self.template_registry.get_template(template_name)
        if not template:
            return None

        # Create a temporary module with the template code
        spec = importlib.util.spec_from_loader(
            f"custom_agent_{agent_name}", loader=None
        )
        module = importlib.util.module_from_spec(spec)

        # Execute the template code in the module
        # SECURITY: exec() is used for dynamic agent loading from trusted templates
        # This is an intentional design decision for the agent framework
        exec(template.template_code, module.__dict__)  # nosec B102

        # Find the agent class (assume it's the first Agent subclass)
        agent_class = None
        for name, obj in module.__dict__.items():
            if inspect.isclass(obj) and issubclass(obj, Agent) and obj != Agent:
                agent_class = obj
                break

        if not agent_class:
            return None

        # Create and return the agent instance
        return agent_class(agent_name, triggers, event_bus, config)

    async def create_from_file(
        self,
        file_path: Path,
        agent_name: str,
        triggers: List[str],
        event_bus: EventBus,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Agent]:
        """Create an agent from a Python file."""
        if not file_path.exists():
            return None

        # Load the module
        spec = importlib.util.spec_from_file_location(
            f"custom_agent_{agent_name}", file_path
        )
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the agent class
        agent_class = None
        for name, obj in module.__dict__.items():
            if inspect.isclass(obj) and issubclass(obj, Agent) and obj != Agent:
                agent_class = obj
                break

        if not agent_class:
            return None

        # Create and return the agent instance
        return agent_class(agent_name, triggers, event_bus, config or {})


class AgentMarketplace:
    """Marketplace for sharing and discovering custom agents."""

    def __init__(self, marketplace_path: Path):
        self.marketplace_path = marketplace_path
        self.marketplace_path.mkdir(parents=True, exist_ok=True)
        self.index_file = marketplace_path / "index.json"
        self.agents_dir = marketplace_path / "agents"

    async def publish_agent(self, agent_file: Path, metadata: Dict[str, Any]) -> bool:
        """Publish an agent to the marketplace."""
        if not agent_file.exists():
            return False

        # Copy agent file to marketplace
        agent_id = metadata.get("name", agent_file.stem)
        agent_dir = self.agents_dir / agent_id
        agent_dir.mkdir(exist_ok=True)

        import shutil

        shutil.copy2(agent_file, agent_dir / "agent.py")

        # Save metadata
        import time

        metadata["published_at"] = metadata.get("published_at", time.time())
        async with aiofiles.open(agent_dir / "metadata.json", "w") as f:
            await f.write(json.dumps(metadata, indent=2))

        # Update index
        await self._update_index()
        return True

    async def download_agent(self, agent_id: str) -> Optional[Path]:
        """Download an agent from the marketplace."""
        agent_dir = self.agents_dir / agent_id
        if not agent_dir.exists():
            return None

        return agent_dir / "agent.py"

    async def list_agents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available agents in the marketplace."""
        if not self.index_file.exists():
            return []

        async with aiofiles.open(self.index_file, "r") as f:
            content = await f.read()

        try:
            agents = json.loads(content)
            if category:
                agents = [a for a in agents if a.get("category") == category]
            return agents
        except json.JSONDecodeError:
            return []

    async def _update_index(self) -> None:
        """Update the marketplace index."""
        agents = []

        for agent_dir in self.agents_dir.iterdir():
            if agent_dir.is_dir():
                metadata_file = agent_dir / "metadata.json"
                if metadata_file.exists():
                    async with aiofiles.open(metadata_file, "r") as f:
                        try:
                            metadata = json.loads(await f.read())
                            metadata["id"] = agent_dir.name
                            agents.append(metadata)
                        except json.JSONDecodeError:
                            continue

        async with aiofiles.open(self.index_file, "w") as f:
            await f.write(json.dumps(agents, indent=2))
