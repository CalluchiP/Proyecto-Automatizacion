import time
from typing import List, Dict, Any

class TelemetryEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelemetryEngine, cls).__new__(cls)
            cls._instance.agents = {}
            cls._instance.total_tickets = 0
            cls._instance.successful_tickets = 0
        return cls._instance

    def register_agent(self, agent_name: str, agent_instance: Any):
        self.agents[agent_name] = agent_instance

    def record_ticket_result(self, success: bool):
        self.total_tickets += 1
        if success:
            self.successful_tickets += 1

    def get_summary(self) -> Dict[str, Any]:
        agent_metrics = []
        total_tokens_all = 0
        all_latencies = []

        for name, agent in self.agents.items():
            metrics = agent.get_metrics()
            agent_metrics.append(metrics)
            total_tokens_all += metrics["total_tokens"]
            all_latencies.extend(agent.latency_log)

        avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
        success_rate = (self.successful_tickets / self.total_tickets * 100.0) if self.total_tickets > 0 else 0.0

        return {
            "total_tickets": self.total_tickets,
            "successful_tickets": self.successful_tickets,
            "success_rate_percent": round(success_rate, 2),
            "average_system_latency_ms": round(avg_latency, 2),
            "total_tokens_consumed": total_tokens_all,
            "agents": agent_metrics
        }

    def reset(self):
        self.total_tickets = 0
        self.successful_tickets = 0
        for agent in self.agents.values():
            agent.latency_log = []
            agent.token_usage_log = []
