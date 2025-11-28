"""Agent behavior learning system for Phase 3."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles


@dataclass
class BehaviorPattern:
    """A learned behavior pattern for an agent."""

    agent_name: str
    pattern_name: str
    description: str
    conditions: Dict[str, Any]
    recommended_action: str
    confidence: float  # 0.0 to 1.0
    frequency: int = 1
    last_observed: Optional[float] = None


class LearningSystem:
    """System for learning from agent behavior and feedback."""

    def __init__(self, storage_path: Path):
        """Initialize learning system.
        
        Args:
            storage_path: Path to store learning data
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.patterns_file = storage_path / "patterns.json"
        self.insights_file = storage_path / "insights.json"

    async def learn_pattern(
        self,
        agent_name: str,
        pattern_name: str,
        description: str,
        conditions: Dict[str, Any],
        recommended_action: str,
        confidence: float = 0.8,
    ) -> None:
        """Learn a behavior pattern from agent execution.
        
        Args:
            agent_name: Name of the agent
            pattern_name: Name of the pattern
            description: Description of the pattern
            conditions: Conditions that trigger the pattern
            recommended_action: Recommended action for this pattern
            confidence: Confidence level (0.0-1.0)
        """
        patterns = await self._load_patterns()
        
        key = f"{agent_name}:{pattern_name}"
        if key in patterns:
            # Update existing pattern
            pattern = patterns[key]
            pattern["frequency"] += 1
            pattern["confidence"] = min(1.0, pattern["confidence"] + 0.05)
        else:
            # Create new pattern
            import time
            pattern = {
                "agent_name": agent_name,
                "pattern_name": pattern_name,
                "description": description,
                "conditions": conditions,
                "recommended_action": recommended_action,
                "confidence": confidence,
                "frequency": 1,
                "last_observed": time.time(),
            }
        
        patterns[key] = pattern
        await self._save_patterns(patterns)

    async def get_patterns_for_agent(self, agent_name: str) -> List[BehaviorPattern]:
        """Get learned patterns for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of learned behavior patterns
        """
        patterns_data = await self._load_patterns()
        patterns = []
        
        for key, data in patterns_data.items():
            if data.get("agent_name") == agent_name:
                patterns.append(
                    BehaviorPattern(
                        agent_name=data["agent_name"],
                        pattern_name=data["pattern_name"],
                        description=data["description"],
                        conditions=data["conditions"],
                        recommended_action=data["recommended_action"],
                        confidence=data["confidence"],
                        frequency=data.get("frequency", 1),
                        last_observed=data.get("last_observed"),
                    )
                )
        
        return sorted(patterns, key=lambda p: p.confidence, reverse=True)

    async def get_recommendations(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get recommendations based on learned patterns.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of recommendations
        """
        patterns = await self.get_patterns_for_agent(agent_name)
        recommendations = []
        
        for pattern in patterns:
            if pattern.confidence >= 0.7:  # Only high-confidence patterns
                recommendations.append({
                    "pattern": pattern.pattern_name,
                    "description": pattern.description,
                    "action": pattern.recommended_action,
                    "confidence": pattern.confidence,
                    "frequency": pattern.frequency,
                })
        
        return recommendations

    async def store_insight(
        self,
        agent_name: str,
        insight_type: str,
        data: Dict[str, Any],
    ) -> None:
        """Store an insight about agent behavior.
        
        Args:
            agent_name: Name of the agent
            insight_type: Type of insight
            data: Insight data
        """
        insights = await self._load_insights()
        
        key = f"{agent_name}:{insight_type}"
        if key in insights:
            insights[key]["count"] += 1
            insights[key]["latest_data"] = data
        else:
            import time
            insights[key] = {
                "agent_name": agent_name,
                "insight_type": insight_type,
                "data": data,
                "latest_data": data,
                "count": 1,
                "first_observed": time.time(),
                "last_observed": time.time(),
            }
        
        insights[key]["last_observed"] = __import__("time").time()
        await self._save_insights(insights)

    async def get_insights_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Get all insights for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary of insights
        """
        insights_data = await self._load_insights()
        agent_insights = {}
        
        for key, data in insights_data.items():
            if data.get("agent_name") == agent_name:
                insight_type = data["insight_type"]
                agent_insights[insight_type] = {
                    "count": data["count"],
                    "data": data.get("latest_data", data.get("data", {})),
                    "first_observed": data.get("first_observed"),
                    "last_observed": data.get("last_observed"),
                }
        
        return agent_insights

    async def suggest_optimization(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Suggest optimizations for an agent based on learning.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Optimization suggestion or None
        """
        insights = await self.get_insights_for_agent(agent_name)
        
        # Analyze patterns
        suggestions = []
        
        if "slow_execution" in insights:
            suggestions.append({
                "issue": "Slow execution detected",
                "suggestion": "Consider increasing debounce time or reducing scope",
                "priority": "medium",
            })
        
        if "high_memory_usage" in insights:
            suggestions.append({
                "issue": "High memory usage",
                "suggestion": "Consider processing files in batches",
                "priority": "high",
            })
        
        if "frequent_errors" in insights:
            suggestions.append({
                "issue": "Frequent errors",
                "suggestion": "Review error handling and edge cases",
                "priority": "high",
            })
        
        if suggestions:
            return suggestions[0]
        
        return None

    async def _load_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load all patterns from file.
        
        Returns:
            Dictionary of patterns
        """
        if not self.patterns_file.exists():
            return {}
        
        async with aiofiles.open(self.patterns_file, "r") as f:
            content = await f.read()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    async def _save_patterns(self, patterns: Dict[str, Dict[str, Any]]) -> None:
        """Save patterns to file.
        
        Args:
            patterns: Dictionary of patterns to save
        """
        async with aiofiles.open(self.patterns_file, "w") as f:
            await f.write(json.dumps(patterns, indent=2))

    async def _load_insights(self) -> Dict[str, Dict[str, Any]]:
        """Load all insights from file.
        
        Returns:
            Dictionary of insights
        """
        if not self.insights_file.exists():
            return {}
        
        async with aiofiles.open(self.insights_file, "r") as f:
            content = await f.read()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    async def _save_insights(self, insights: Dict[str, Dict[str, Any]]) -> None:
        """Save insights to file.
        
        Args:
            insights: Dictionary of insights to save
        """
        async with aiofiles.open(self.insights_file, "w") as f:
            await f.write(json.dumps(insights, indent=2))


class AdaptiveAgentConfig:
    """Adaptive configuration that learns from behavior."""

    def __init__(self, learning_system: LearningSystem, agent_name: str):
        """Initialize adaptive config.
        
        Args:
            learning_system: Learning system instance
            agent_name: Name of the agent
        """
        self.learning_system = learning_system
        self.agent_name = agent_name
        self._config_cache: Dict[str, Any] = {}

    async def get_optimal_parameters(self) -> Dict[str, Any]:
        """Get parameters optimized based on learning.
        
        Returns:
            Optimized configuration parameters
        """
        insights = await self.learning_system.get_insights_for_agent(self.agent_name)
        parameters = {
            "debounce_seconds": 1.0,
            "timeout_seconds": 30,
            "retry_count": 3,
            "batch_size": 10,
        }
        
        # Adapt based on insights
        if "slow_execution" in insights:
            parameters["debounce_seconds"] = 2.0
            parameters["batch_size"] = 5
        
        if "frequent_errors" in insights:
            parameters["retry_count"] = 5
        
        return parameters

    async def should_execute(self) -> bool:
        """Determine if agent should execute based on learning.
        
        Returns:
            True if agent should execute
        """
        insights = await self.learning_system.get_insights_for_agent(self.agent_name)
        
        # Skip if too many recent errors
        if "frequent_errors" in insights:
            error_count = insights["frequent_errors"]["count"]
            if error_count > 10:
                return False
        
        return True
