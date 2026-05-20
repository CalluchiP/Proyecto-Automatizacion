from antigravity import EventBus

def get_event_bus() -> EventBus:
    event_bus = EventBus()
    
    # Register events specified in GEMINI.md
    event_bus.register_events([
        "ticket.creado",
        "diagnostico.completado",
        "presupuesto.generado",
        "inventario.verificado",
        "reparacion.iniciada",
        "reparacion.completada",
        "calidad.aprobada",
        "cliente.notificado",
        "venta.procesada"  # Emitted by Sales Agent
    ])
    
    return event_bus
