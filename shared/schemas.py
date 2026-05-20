MCP_COMMUNICATION_SCHEMA = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["ticket_id", "evento", "agente_emisor", "timestamp", "payload"],
  "properties": {
    "ticket_id": { "type": "string" },
    "evento": { "type": "string" },
    "agente_emisor": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": { "type": "object" }
  }
}

TICKET_SHARED_SCHEMA = {
  "type": "object",
  "required": [
    "ticket_id", "cliente", "tipo_solicitud", "equipo", 
    "diagnostico", "inventario", "estado_ticket", "historial_conversacion"
  ],
  "properties": {
    "ticket_id": { "type": "string" },
    "cliente": {
      "type": "object",
      "required": ["nombre", "contacto", "canal_preferido"],
      "properties": {
        "nombre": { "type": "string" },
        "contacto": { "type": "string" },
        "canal_preferido": { "type": "string", "enum": ["email", "sms", "whatsapp"] }
      }
    },
    "tipo_solicitud": { "type": "string", "enum": ["venta", "reparacion", "soporte"] },
    "equipo": {
      "type": "object",
      "required": ["descripcion", "sintomas", "marca_modelo"],
      "properties": {
        "descripcion": { "type": "string" },
        "sintomas": { "type": "array", "items": { "type": "string" } },
        "marca_modelo": { "type": "string" }
      }
    },
    "diagnostico": {
      "type": "object",
      "required": ["informe", "piezas_requeridas", "costo_estimado", "tiempo_estimado_horas"],
      "properties": {
        "informe": { "type": "string" },
        "piezas_requeridas": { "type": "array", "items": { "type": "object" } },
        "costo_estimado": { "type": "number" },
        "tiempo_estimado_horas": { "type": "integer" }
      }
    },
    "inventario": {
      "type": "object",
      "required": ["disponible", "piezas_confirmadas", "orden_aprovisionamiento"],
      "properties": {
        "disponible": { "type": "boolean" },
        "piezas_confirmadas": { "type": "array", "items": { "type": "string" } },
        "orden_aprovisionamiento": { "type": "string" }
      }
    },
    "estado_ticket": { "type": "string" },
    "historial_conversacion": { "type": "array", "items": { "type": "object" } }
  }
}
