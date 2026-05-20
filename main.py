import os
import sys
import json
import time

# Ensure current directory is in python path so local antigravity package is imported first
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from antigravity import AgentGraph, SharedMemory, EventBus
from antigravity.engine import TelemetryEngine
from shared.memory import get_shared_memory
from shared.event_bus import get_event_bus
from agents import (
    Orchestrator,
    CustomerServiceAgent,
    TechnicalDiagnosisAgent,
    SalesAgent,
    WarehouseAgent,
    NotificationsAgent
)

def build_graph() -> AgentGraph:
    graph = AgentGraph(name="servicio_tecnico_graph")

    # Add agent nodes
    graph.add_node("orquestador", role="orchestrator")
    graph.add_node("atencion_cliente", role="subagent")
    graph.add_node("tecnico_diagnostico", role="subagent")
    graph.add_node("ventas", role="subagent")
    graph.add_node("almacen", role="subagent")
    graph.add_node("notificaciones", role="subagent")

    # Add edges
    graph.add_edge("orquestador", "atencion_cliente")
    graph.add_edge("orquestador", "tecnico_diagnostico")
    graph.add_edge("orquestador", "ventas")
    graph.add_edge("orquestador", "almacen")
    graph.add_edge("orquestador", "notificaciones")
    graph.add_edge("tecnico_diagnostico", "almacen")   # solicitud de repuestos
    graph.add_edge("almacen", "tecnico_diagnostico")    # confirmación de stock
    
    return graph

def run_ticket_simulation(ticket_id: str, client_input: str, follow_up_input: str = None) -> bool:
    print("\n" + "="*80)
    print(f" PROCESANDO TICKET: {ticket_id}")
    print(f" INPUT CLIENTE: \"{client_input}\"")
    print("="*80 + "\n")
    
    # 1. Initialize memory and event bus
    shared_memory = get_shared_memory()
    event_bus = get_event_bus()
    telemetry = TelemetryEngine()
    
    # Initialize basic shared state
    shared_memory.initialize_state({
        "ticket_id": ticket_id,
        "cliente": {},
        "tipo_solicitud": "",
        "equipo": {},
        "diagnostico": {},
        "inventario": {},
        "estado_ticket": "recibido",
        "historial_conversacion": []
    })

    # 2. Instantiate and register agents in TelemetryEngine
    orquestador = Orchestrator()
    atencion_cliente = CustomerServiceAgent()
    tecnico_diagnostico = TechnicalDiagnosisAgent()
    ventas = SalesAgent()
    almacen = WarehouseAgent()
    notificaciones = NotificationsAgent()

    # Register for metrics
    telemetry.register_agent("orquestador", orquestador)
    telemetry.register_agent("atencion_cliente", atencion_cliente)
    telemetry.register_agent("tecnico_diagnostico", tecnico_diagnostico)
    telemetry.register_agent("ventas", ventas)
    telemetry.register_agent("almacen", almacen)
    telemetry.register_agent("notificaciones", notificaciones)

    subagents = {
        "atencion_cliente": atencion_cliente,
        "tecnico_diagnostico": tecnico_diagnostico,
        "ventas": ventas,
        "almacen": almacen,
        "notificaciones": notificaciones
    }

    # 3. Register Notifications Agent to events in EventBus
    # For simulation, we'll let Orchestrator invoke it directly to model sequential prints,
    # but we also subscribe it here for true EventBus behavior.
    def notification_subscriber(mcp_message):
        # Prevent double notifications in console
        pass
    
    event_bus.subscribe("ticket.creado", notification_subscriber)
    event_bus.subscribe("diagnostico.completado", notification_subscriber)
    event_bus.subscribe("presupuesto.generado", notification_subscriber)
    event_bus.subscribe("reparacion.iniciada", notification_subscriber)
    event_bus.subscribe("reparacion.completada", notification_subscriber)
    event_bus.subscribe("calidad.aprobada", notification_subscriber)
    event_bus.subscribe("venta.procesada", notification_subscriber)

    # 4. Run the Orchestrator loop
    success = orquestador.process_ticket(shared_memory, event_bus, subagents, client_input, ticket_id)
    
    # If ambiguous, run the follow up input
    if not success and shared_memory.get("estado_ticket") == "recibido" and follow_up_input:
        print("\n\033[93m[Simulador] -> Cliente provee aclaración interactiva...\033[0m")
        print(f"\033[93m[Simulador] Aclaración Cliente: \"{follow_up_input}\"\033[0m\n")
        success = orquestador.process_ticket(shared_memory, event_bus, subagents, follow_up_input, ticket_id)

    # Record the result in metrics
    telemetry.record_ticket_result(success)
    
    print("\n" + "-"*80)
    print(f" RESULTADO FINAL DEL TICKET {ticket_id}: {'COMPLETADO CON ÉXITO' if success else 'RECHAZADO/PENDIENTE'}")
    print(f" Estado Final en SharedMemory: {shared_memory.get('estado_ticket')}")
    print("-"*80 + "\n")
    
    return success

def main():
    print("\033[1;92m" + "="*80)
    print(" INICIALIZANDO SISTEMA MULTIAGENTE TECHSERV (ANTIGRAVITY + CLAUDE CODE)")
    print("="*80 + "\033[0m")
    
    # Reset/clear metrics database
    telemetry = TelemetryEngine()
    telemetry.reset()
    
    # Build and validate the Agent Graph
    graph = build_graph()
    
    # 5 Test cases from GEMINI.md
    tickets = [
        {
            "id": "TKT-2026-001",
            "input": "Hola, me llamo Carlos Pérez, mi cel es +5491133334444 y prefiero whatsapp. Mi laptop HP tiene la pantalla rota.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-002",
            "input": "Buenas, soy Sofía Gómez, mi email es sofia@gmail.com, celular +5491155556666, prefiero sms. Mi PC gamer de escritorio no arranca para nada.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-003",
            "input": "Hola, me llamo Alejandro Ruiz, contacto al@gmail.com, prefiero email. Quiero comprar un SSD 1TB para actualizar mi equipo.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-004",
            "input": "Hola, soy Mateo Torres, celular +5491188887777, prefiero whatsapp. Mi tablet con teclado no responde bluetooth.",
            "follow_up": None
        },
        {
            "id": "TKT-2026-005",
            "input": "Hola, me llamo Lucía y mi compu no anda.", # Ambiguous!
            "follow_up": "Es una Laptop Dell Inspiron, se calienta demasiado y se apaga a los 10 minutos de uso. Mi contacto es lucia@outlook.com y prefiero email."
        }
    ]
    
    # Run all tickets
    for t in tickets:
        run_ticket_simulation(t["id"], t["input"], t["follow_up"])
        time.sleep(1.0) # Pause between tickets for readable log stream
        
    # Get and print final metrics summary
    summary = telemetry.get_summary()
    
    print("\n" + "="*80)
    print(" REPORTES DE MÉTRICAS GLOBALES DEL SISTEMA (TELEMETRÍA)")
    print("="*80)
    print(f"Tickets Totales Procesados: {summary['total_tickets']}")
    print(f"Tickets Exitosos (Autónomos): {summary['successful_tickets']}")
    print(f"Tasa de Éxito: {summary['success_rate_percent']}%")
    print(f"Latencia Promedio del Sistema: {summary['average_system_latency_ms']} ms")
    print(f"Uso Total de Tokens Estimados: {summary['total_tokens_consumed']} tokens")
    print("-"*80)
    print(" Desglose de Telemetría por Agente:")
    print("-"*80)
    for a in summary["agents"]:
        print(f" Agente: {a['name']:<20} | Rol: {a['role']:<15} | Llamadas: {a['calls']:<3} | Latencia Prom: {a['avg_latency_ms']:<6} ms | Tokens: {a['total_tokens']}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
