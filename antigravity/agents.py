import time
import json
from typing import Dict, Any, List

class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str = ""):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.latency_log: List[float] = []
        self.token_usage_log: List[int] = []

    def log_telemetry(self, start_time: float, text_in: str, text_out: str):
        duration_ms = (time.time() - start_time) * 1000.0
        self.latency_log.append(duration_ms)
        
        # Simple token estimation: ~4 characters per token
        tokens_in = len(text_in) // 4
        tokens_out = len(text_out) // 4
        self.token_usage_log.append(tokens_in + tokens_out)

    def get_metrics(self) -> Dict[str, Any]:
        avg_latency = sum(self.latency_log) / len(self.latency_log) if self.latency_log else 0.0
        total_tokens = sum(self.token_usage_log)
        return {
            "name": self.name,
            "role": self.role,
            "calls": len(self.latency_log),
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens": total_tokens
        }

class OrchestratorAgent(BaseAgent):
    def __init__(self, name: str, system_prompt: str = ""):
        super().__init__(name, role="orchestrator", system_prompt=system_prompt)

    def handle_request(self, shared_memory: Any, event_bus: Any, event_name: str, payload: Dict[str, Any]) -> None:
        """
        To be overridden by the child class in agents/orquestador.py
        """
        pass

class SubAgent(BaseAgent):
    def __init__(self, name: str, system_prompt: str = ""):
        super().__init__(name, role="subagent", system_prompt=system_prompt)

    def process(self, shared_memory: Any, event_bus: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        To be overridden by child subclasses
        """
        return {}
