"""Agent pipeline for sequential execution with short-circuit on failure."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .agent import Agent, AgentResult
from .event import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class PipelineStageResult:
    """Result of a single pipeline stage."""

    agent_name: str
    result: AgentResult
    skipped: bool = False


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""

    pipeline_name: str
    success: bool
    duration: float
    stages: List[PipelineStageResult] = field(default_factory=list)
    short_circuited: bool = False
    short_circuit_at: Optional[str] = None

    @property
    def message(self) -> str:
        completed = [s for s in self.stages if not s.skipped]
        if self.success:
            return f"Pipeline '{self.pipeline_name}': {len(completed)}/{len(self.stages)} stages passed"
        failed = [s for s in completed if not s.result.success]
        failed_names = ", ".join(s.agent_name for s in failed)
        return f"Pipeline '{self.pipeline_name}': failed at {failed_names}"


class Pipeline:
    """Executes a sequence of agents in order with short-circuit on failure.

    A pipeline subscribes to events like a regular agent, but instead of
    handling events independently, it runs its stages sequentially. If any
    stage fails and short_circuit is enabled, remaining stages are skipped.
    """

    def __init__(
        self,
        name: str,
        stages: List[Agent],
        event_bus: EventBus,
        triggers: List[str],
        short_circuit: bool = True,
    ):
        self.name = name
        self.stages = stages
        self.event_bus = event_bus
        self.triggers = triggers
        self.short_circuit = short_circuit
        self.enabled = True
        self._running = False
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._process_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(f"pipeline.{name}")

    async def start(self) -> None:
        """Start the pipeline, subscribing to its trigger events."""
        if self._running:
            return

        self._running = True

        for trigger in self.triggers:
            await self.event_bus.subscribe(trigger, self._event_queue)

        self._process_task = asyncio.create_task(self._process_events())
        stage_names = " → ".join(s.name for s in self.stages)
        self.logger.info(
            f"Pipeline '{self.name}' started: {stage_names} "
            f"(triggers: {self.triggers}, short_circuit: {self.short_circuit})"
        )

    async def stop(self) -> None:
        """Stop the pipeline."""
        if not self._running:
            return

        self._running = False

        for trigger in self.triggers:
            await self.event_bus.unsubscribe(trigger, self._event_queue)

        if self._process_task and not self._process_task.done():
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass

        self.logger.info(f"Pipeline '{self.name}' stopped")

    async def execute(self, event: Event) -> PipelineResult:
        """Execute all pipeline stages sequentially.

        Args:
            event: The triggering event to pass to each stage.

        Returns:
            PipelineResult with per-stage results.
        """
        start_time = time.time()
        stage_results: List[PipelineStageResult] = []
        all_success = True
        short_circuited = False
        short_circuit_at = None

        for stage in self.stages:
            if not stage.enabled:
                stage_results.append(
                    PipelineStageResult(
                        agent_name=stage.name,
                        result=AgentResult(
                            agent_name=stage.name,
                            success=True,
                            duration=0.0,
                            message="Skipped (disabled)",
                        ),
                        skipped=True,
                    )
                )
                continue

            if short_circuited:
                stage_results.append(
                    PipelineStageResult(
                        agent_name=stage.name,
                        result=AgentResult(
                            agent_name=stage.name,
                            success=False,
                            duration=0.0,
                            message=f"Skipped (short-circuited at {short_circuit_at})",
                        ),
                        skipped=True,
                    )
                )
                continue

            try:
                result = await stage.handle(event)
                stage_results.append(
                    PipelineStageResult(agent_name=stage.name, result=result)
                )

                if not result.success:
                    all_success = False
                    if self.short_circuit:
                        short_circuited = True
                        short_circuit_at = stage.name
                        self.logger.warning(
                            f"Pipeline '{self.name}' short-circuited at '{stage.name}': "
                            f"{result.message}"
                        )

            except Exception as e:
                self.logger.error(
                    f"Pipeline '{self.name}' stage '{stage.name}' error: {e}"
                )
                error_result = AgentResult(
                    agent_name=stage.name,
                    success=False,
                    duration=0.0,
                    error=str(e),
                    message=f"Exception: {e}",
                )
                stage_results.append(
                    PipelineStageResult(agent_name=stage.name, result=error_result)
                )
                all_success = False
                if self.short_circuit:
                    short_circuited = True
                    short_circuit_at = stage.name

        duration = time.time() - start_time

        return PipelineResult(
            pipeline_name=self.name,
            success=all_success,
            duration=duration,
            stages=stage_results,
            short_circuited=short_circuited,
            short_circuit_at=short_circuit_at,
        )

    async def _process_events(self) -> None:
        """Process events from the queue by running the pipeline."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if not self.enabled:
                continue

            try:
                result = await self.execute(event)

                # Publish pipeline completion event
                await self.event_bus.emit(
                    Event(
                        type=f"pipeline:{self.name}:completed",
                        payload={
                            "pipeline_name": self.name,
                            "success": result.success,
                            "duration": result.duration,
                            "stages": [
                                {
                                    "agent": s.agent_name,
                                    "success": s.result.success,
                                    "skipped": s.skipped,
                                    "message": s.result.message,
                                    "duration": s.result.duration,
                                }
                                for s in result.stages
                            ],
                            "short_circuited": result.short_circuited,
                            "short_circuit_at": result.short_circuit_at,
                        },
                        source=self.name,
                    )
                )

                status = "✓" if result.success else "✗"
                self.logger.info(f"{status} {result.message} ({result.duration:.2f}s)")

            except Exception as e:
                self.logger.error(
                    f"Error in pipeline '{self.name}': {e}", exc_info=True
                )
