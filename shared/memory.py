from antigravity import SharedMemory

def get_shared_memory() -> SharedMemory:
    shared_memory = SharedMemory()
    
    # Register the primary schema types as defined in GEMINI.md
    shared_memory.schema = {
        "ticket_id": str,
        "cliente": dict,             # client object: {nombre: str, contacto: str, canal_preferido: str}
        "tipo_solicitud": str,        # venta | reparacion | soporte
        "equipo": dict,              # equipment object: {descripcion: str, sintomas: list, marca_modelo: str}
        "diagnostico": dict,         # technical diagnosis details
        "inventario": dict,          # stock status and components order
        "estado_ticket": str,         # recibido | en_diagnostico | presupuestado | en_reparacion | listo | entregado
        "historial_conversacion": list
    }
    
    return shared_memory
