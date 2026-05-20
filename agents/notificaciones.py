from typing import Dict, Any
from antigravity.agents import SubAgent
from antigravity import SharedMemory, EventBus

class NotificationsAgent(SubAgent):
    def __init__(self):
        system_prompt = (
            "Eres el Agente de Notificaciones del servicio técnico.\n"
            "Tu única responsabilidad es:\n"
            "1. Escuchar los eventos del Event Bus: ticket.creado, diagnostico.completado, \n"
            "   presupuesto.generado, reparacion.completada, calidad.aprobada.\n"
            "2. Redactar un mensaje claro y profesional para el cliente al ocurrir cada evento.\n"
            "3. Enviar la notificación por el canal preferido registrado en Memoria Compartida \n"
            "   (email, SMS o WhatsApp simulado).\n"
            "4. Registrar cada notificación enviada en el historial del ticket.\n"
            "No tomes decisiones técnicas. Solo comunica estados al cliente."
        )
        super().__init__(name="notificaciones", system_prompt=system_prompt)

    def process(self, shared_memory: SharedMemory, event_bus: EventBus, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reacts to incoming payload. Note: The notifications agent listens directly.
        We can also invoke it programmatically.
        """
        # Read customer and ticket state from memory
        ticket_id = shared_memory.get("ticket_id")
        cliente = shared_memory.get("cliente") or {}
        nombre = cliente.get("nombre", "Cliente")
        contacto = cliente.get("contacto", "N/A")
        canal = cliente.get("canal_preferido", "email").upper()
        
        evento = payload.get("evento", "actualización_estado")
        message_text = ""

        # Draft message based on event
        if evento == "ticket.creado":
            equipo = shared_memory.get("equipo") or {}
            desc = equipo.get("descripcion", "su equipo")
            message_text = (
                f"Hola {nombre}. Hemos registrado tu solicitud técnica para '{desc}'. "
                f"Tu Ticket ID es {ticket_id}. Te informaremos apenas tengamos el diagnóstico."
            )
        elif evento == "diagnostico.completado":
            diag = shared_memory.get("diagnostico") or {}
            costo = diag.get("costo_estimado", 0.0)
            message_text = (
                f"Estimado {nombre}, el diagnóstico técnico para tu equipo está listo. "
                f"Costo estimado: ${costo:.2f}. Detalle: {diag.get('informe', '')}"
            )
        elif evento == "presupuesto.generado":
            diag = shared_memory.get("diagnostico") or {}
            costo = diag.get("costo_estimado", 0.0)
            horas = diag.get("tiempo_estimado_horas", 0)
            message_text = (
                f"TechServ PRESUPUESTO: Hola {nombre}, el presupuesto final es de ${costo:.2f}. "
                f"Tiempo estimado: {horas} horas. Por favor responde 'APROBAR' para iniciar la reparación."
            )
        elif evento == "reparacion.iniciada":
            message_text = f"TechServ: Hola {nombre}. Hemos iniciado la reparación física de tu equipo. Te avisaremos al terminar."
        elif evento == "reparacion.completada":
            message_text = f"TechServ: Hola {nombre}. La reparación ha finalizado con éxito. Procediendo a control de calidad."
        elif evento == "calidad.aprobada":
            message_text = (
                f"¡Buenas noticias {nombre}! Tu equipo ha superado exitosamente el control de calidad "
                f"y se encuentra LISTO para retiro. Puedes pasar por nuestro local. ¡Gracias por confiar en TechServ!"
            )
        elif evento == "venta.procesada":
            diag = shared_memory.get("diagnostico") or {}
            costo = diag.get("costo_estimado", 0.0)
            message_text = (
                f"Compra Confirmada: Hola {nombre}, tu pago de ${costo:.2f} ha sido procesado exitosamente. "
                f"Tu orden está lista para entrega/despacho. ¡Gracias por tu compra!"
            )
        elif evento == "ticket.error":
            err_msg = payload.get("error_msg", "un inconveniente inesperado")
            message_text = (
                f"Hola {nombre}. Te informamos que hemos detectado un inconveniente técnico con tu ticket ({ticket_id}) "
                f"debido a: {err_msg}. Nuestro equipo de soporte ha sido alertado para resolverlo a la brevedad."
            )
        else:
            message_text = f"Hola {nombre}, te informamos que el estado de tu ticket {ticket_id} es ahora: {evento}."

        # Simulate sending notification
        print(f"\033[95m[Agente Notificaciones] ENVIANDO POR {canal} a {contacto}:\033[0m")
        print(f"\033[95m    >>> \"{message_text}\"\033[0m")

        # Save to Shared Memory history
        historial = shared_memory.get("historial_conversacion") or []
        historial.append({
            "sender": self.name,
            "canal": canal,
            "destinatario": contacto,
            "message": message_text
        })
        shared_memory.set("historial_conversacion", historial, self.name)
        
        # Publish event
        # To avoid infinite recursion, we just return the result
        return {
            "ticket_id": ticket_id,
            "canal_enviado": canal,
            "destinatario": contacto,
            "mensaje": message_text
        }
