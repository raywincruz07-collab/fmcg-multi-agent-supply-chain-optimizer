from abc import ABC, abstractmethod
from typing import Dict, Any
from fmcg_supply_chain.orchestration.state import AgentResult, PipelineState
import time


class BaseAgent(ABC):
    """
    Abstract base class for all deterministic pipeline agents.
    Enforces a strict input/output contract.
    """

    def __init__(self, name: str):
        self.name = name

    def execute(self, state: PipelineState) -> AgentResult:
        """
        Executes the agent logic.
        Wraps the internal _run method to provide timing and standardized error handling.
        """
        start_time = time.time()
        result = AgentResult(agent_name=self.name, status="pending")

        try:
            state.log_trace(self.name, "Start Execution", f"Agent {self.name} began execution.")
            self._run(state, result)
            result.status = "success"
            state.log_trace(self.name, "End Execution", f"Agent {self.name} finished successfully.")
        except Exception as e:
            result.status = "error"
            result.warnings.append(str(e))
            state.log_trace(self.name, "Execution Error", str(e))

        result.execution_duration_sec = round(time.time() - start_time, 2)
        state.agent_results[self.name] = result
        return result

    @abstractmethod
    def _run(self, state: PipelineState, result: AgentResult) -> None:
        """
        Internal implementation of the agent's core logic.
        Must mutate the `result` object in-place.
        """
        pass
