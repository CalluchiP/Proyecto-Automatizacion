import time
import datetime
import json
from typing import Dict, Any, List, Callable
from antigravity.engine import TelemetryEngine

class AgentGraph:
    def __init__(self, name: str):
        self.name = name
        self.nodes = {}
        self.edges = []

    def add_node(self, node_name: str, role: str):
        self.nodes[node_name] = role
        print(f"\033[92m[AgentGraph] Nodo agregado: {node_name} ({role})\033[0m")

    def add_edge(self, source: str, target: str):
        self.edges.append((source, target))
        print(f"\033[92m[AgentGraph] Arista agregada: {source} -> {target}\033[0m")


class SharedMemory:
    def __init__(self):
        self.schema = {}
        self.state = {}
        self.history = []

    def initialize_state(self, initial_values: Dict[str, Any]):
        self.state = initial_values.copy()
        # Verify schema
        self._validate_schema(self.state)

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any, agent_name: str):
        """
        Set value in shared memory and track changes.
        """
        old_value = self.state.get(key)
        self.state[key] = value
        self._validate_schema(self.state)
        
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "key": key,
            "agent": agent_name,
            "old_value": old_value,
            "new_value": value
        }
        self.history.append(log_entry)
        
        # Format list value or other values nicely in the console print
        print(f"\033[95m[SharedMemory] {agent_name} modificó '{key}': {old_value} -> {value}\033[0m")

    def _validate_schema(self, state: Dict[str, Any]):
        # Perform rigorous recursive JSON Schema validation using TICKET_SHARED_SCHEMA from shared/schemas
        from shared.schemas import TICKET_SHARED_SCHEMA
        self._validate_value(state, TICKET_SHARED_SCHEMA, "state")

    def _validate_value(self, value: Any, schema: Dict[str, Any], path: str):
        schema_type = schema.get("type")
        if schema_type == "object":
            if not isinstance(value, dict):
                raise TypeError(f"Schema Violation at '{path}': Expected dict, got {type(value).__name__}")
            
            # If the dict is empty, allow it as an uninitialized progressive slot
            if not value:
                return
            
            # Check required fields
            required = schema.get("required", [])
            for req in required:
                if req not in value:
                    raise ValueError(f"Schema Violation at '{path}': Missing required property '{req}'")
            
            # Validate properties recursively
            properties = schema.get("properties", {})
            for k, val in value.items():
                if k in properties:
                    self._validate_value(val, properties[k], f"{path}.{k}")
        
        elif schema_type == "array":
            if not isinstance(value, list):
                raise TypeError(f"Schema Violation at '{path}': Expected list, got {type(value).__name__}")
            items_schema = schema.get("items")
            if items_schema:
                for idx, item in enumerate(value):
                    self._validate_value(item, items_schema, f"{path}[{idx}]")
                    
        elif schema_type == "string":
            if not isinstance(value, str):
                raise TypeError(f"Schema Violation at '{path}': Expected str, got {type(value).__name__}")
            # If empty string, allow it as an uninitialized progressive slot
            if value == "":
                return
            enum_vals = schema.get("enum")
            if enum_vals and value not in enum_vals:
                raise ValueError(f"Schema Violation at '{path}': Value '{value}' not in allowed enum {enum_vals}")
                
        elif schema_type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"Schema Violation at '{path}': Expected float/int, got {type(value).__name__}")
                
        elif schema_type == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"Schema Violation at '{path}': Expected int, got {type(value).__name__}")
                
        elif schema_type == "boolean":
            if not isinstance(value, bool):
                raise TypeError(f"Schema Violation at '{path}': Expected bool, got {type(value).__name__}")


class EventBus:
    def __init__(self):
        self.registered_events = set()
        self.subscribers = {}

    def register_events(self, events: List[str]):
        for ev in events:
            self.registered_events.add(ev)
            print(f"\033[96m[EventBus] Evento registrado: '{ev}'\033[0m")

    def subscribe(self, event_name: str, callback: Callable):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)
        print(f"\033[96m[EventBus] Suscripción registrada para '{event_name}'\033[0m")

    def publish(self, event_name: str, ticket_id: str, emitter: str, payload: Dict[str, Any]):
        if event_name not in self.registered_events:
            print(f"\033[91m[EventBus WARNING] Evento '{event_name}' no registrado previamente en el EventBus!\033[0m")
            self.registered_events.add(event_name)

        timestamp = datetime.datetime.now().isoformat()
        
        # Enforce MCP JSON Schema validation
        mcp_message = {
            "ticket_id": ticket_id,
            "evento": event_name,
            "agente_emisor": emitter,
            "timestamp": timestamp,
            "payload": payload
        }
        
        self._validate_mcp(mcp_message)
        print(f"\033[96m[EventBus MCP PUBLISH] Evento '{event_name}' publicado por '{emitter}'. ticket_id: {ticket_id}\033[0m")
        print(f"\033[90m{json.dumps(mcp_message, indent=2, ensure_ascii=False)}\033[0m")

        # Notify subscribers
        if event_name in self.subscribers:
            for callback in self.subscribers[event_name]:
                callback(mcp_message)

    def _validate_mcp(self, message: Dict[str, Any]):
        required = ["ticket_id", "evento", "agente_emisor", "timestamp", "payload"]
        for field in required:
            if field not in message:
                raise ValueError(f"MCP Schema Violation: Missing required field '{field}'")
        
        if not isinstance(message["ticket_id"], str):
            raise TypeError("MCP Schema Violation: ticket_id must be a string")
        if not isinstance(message["evento"], str):
            raise TypeError("MCP Schema Violation: evento must be a string")
        if not isinstance(message["agente_emisor"], str):
            raise TypeError("MCP Schema Violation: agente_emisor must be a string")
        if not isinstance(message["timestamp"], str):
            raise TypeError("MCP Schema Violation: timestamp must be a string")
        if not isinstance(message["payload"], dict):
            raise TypeError("MCP Schema Violation: payload must be an object (dict)")


class Swarm:
    def __init__(self, agents: List[str], mode: str = "parallel", trigger_event: str = None, join_condition: str = "all_completed"):
        self.agents = agents
        self.mode = mode
        self.trigger_event = trigger_event
        self.join_condition = join_condition
        print(f"\033[93m[Swarm] Swarm configurado. Agentes: {self.agents}. Modo: {self.mode}. Trigger: {self.trigger_event}\033[0m")

    def run_parallel(self, shared_memory: SharedMemory, event_bus: EventBus, payload: Dict[str, Any], agent_instances: Dict[str, Any]) -> List[Dict[str, Any]]:
        print(f"\033[93m[Swarm SwarmRun] Ejecutando agentes en paralelo (hilos reales): {self.agents}...\033[0m")
        results = []
        
        from concurrent.futures import ThreadPoolExecutor
        
        def run_single_agent(name: str):
            if name in agent_instances:
                agent = agent_instances[name]
                start_t = time.time()
                print(f"\033[93m[Swarm] -> Iniciando agente en hilo secundario: {name}\033[0m")
                out = agent.process(shared_memory, event_bus, payload)
                agent.log_telemetry(start_t, str(payload), str(out))
                return {"agent": name, "result": out}
            else:
                print(f"\033[91m[Swarm ERROR] Agente '{name}' no encontrado en las instancias registradas.\033[0m")
                return {"agent": name, "result": None}

        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            # Map returns results in the order of self.agents
            results = list(executor.map(run_single_agent, self.agents))
            
        print(f"\033[93m[Swarm SwarmJoin] Barrera de sincronización: '{self.join_condition}' cumplida para {self.agents}\033[0m")
        return results
