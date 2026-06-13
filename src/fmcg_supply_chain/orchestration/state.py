from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import pandas as pd


@dataclass
class AgentResult:
    """Standardized output contract for all agents."""

    agent_name: str
    status: str  # "success" or "error"
    metrics: Dict[str, Any] = field(default_factory=dict)
    dataframes: Dict[str, pd.DataFrame] = field(default_factory=dict)
    rationale: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_duration_sec: float = 0.0


@dataclass
class PipelineState:
    """State object passed and mutated through the orchestrator pipeline."""

    config: Dict[str, Any]
    master_df: pd.DataFrame
    metadata: Dict[str, Any]

    # Store results from each agent execution
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)

    # Orchestration Trace
    trace: List[Dict[str, Any]] = field(default_factory=list)

    def log_trace(self, agent: str, action: str, details: str):
        self.trace.append({"agent": agent, "action": action, "details": details})
