"""Core framework components."""

from .action_logger import ActionLogger, CLIAction, get_action_logger, log_cli_command
from .agent import Agent, AgentResult
from .amp_thread_mapper import (
    AgentAction,
    AmpThreadEntry,
    AmpThreadMapper,
    ThreadInsight,
    UserManualAction,
    get_amp_thread_mapper,
)
from .config import Config, ConfigWrapper
from .config_schema import (
    CURRENT_SCHEMA_VERSION,
    ConfigMigrationError,
    ConfigValidationError,
    migrate_config,
    validate_config,
)
from .context_store import context_store
from .daemon_health import DaemonHealthCheck, check_daemon_health
from .event import Event, EventBus, Priority
from .event_store import event_store
from .manager import AgentManager
from .pattern_analyzer import (
    Pattern,
    PatternAnalyzer,
    PatternContext,
    PatternDefinitions,
    PatternMatch,
)
from .pattern_detector import (
    DetectedPattern,
    PatternDetector,
    get_pattern_detector,
)
from .transactional_io import (
    ChecksumMismatchError,
    SelfHealing,
    TransactionalFile,
    TransactionError,
    TransactionRecovery,
    initialize_transaction_system,
)

__all__ = [
    "Action Logger",
    "ActionLogger",
    "Agent",
    "AgentAction",
    "AgentResult",
    "AmpThreadEntry",
    "AmpThreadMapper",
    "check_daemon_health",
    "CLIAction",
    "Config",
    "ConfigMigrationError",
    "ConfigValidationError",
    "ConfigWrapper",
    "context_store",
    "CURRENT_SCHEMA_VERSION",
    "DaemonHealthCheck",
    "DetectedPattern",
    "Event",
    "EventBus",
    "event_store",
    "get_action_logger",
    "get_amp_thread_mapper",
    "get_pattern_detector",
    "log_cli_command",
    "migrate_config",
    "Pattern",
    "PatternAnalyzer",
    "PatternContext",
    "PatternDefinitions",
    "PatternDetector",
    "PatternMatch",
    "Priority",
    "AgentManager",
    "ChecksumMismatchError",
    "initialize_transaction_system",
    "SelfHealing",
    "ThreadInsight",
    "TransactionalFile",
    "TransactionError",
    "TransactionRecovery",
    "UserManualAction",
    "validate_config",
]
