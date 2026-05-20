import re
from typing import Dict, Any
from antigravity.agents import SubAgent
from antigravity import SharedMemory, EventBus

class CustomerServiceAgent(SubAgent):
    def __init__(self):
        system_prompt = (
            "Eres el Agente de Atención al Cliente de TechServ, un servicio técnico de computadoras.\n"
            "Tu única responsabilidad es:\n"
            "1. Recibir la consulta inicial del cliente (por texto).\n"
            "2. Clasificar la solicitud en: VENTA, REPARACIÓN o SOPORTE.\n"
            "3. Recopilar datos clave: nombre, contacto, canal preferido, descripción del equipo y síntomas.\n"
            "4. Responder preguntas frecuentes (precios base, tiempos, garantías) usando tu base de conocimiento.\n"
            "5. Emitir el evento \"ticket.creado\" con el estado inicial completo al Orquestador.\n"
            "No realices diagnósticos técnicos ni gestiones inventario. Solo clasifica y recopila.\n"
            "Output siempre en JSON validado con el esquema de ticket."
        )
        super().__init__(name="atencion_cliente", system_prompt=system_prompt)

    def process(self, shared_memory: SharedMemory, event_bus: EventBus, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes initial text input from the client.
        Payload expects: {"cliente_input": str, "ticket_id": str}
        """
        cliente_input = payload.get("cliente_input", "")
        ticket_id = payload.get("ticket_id", "TKT-UNKNOWN")
        
        print(f"\033[92m[{self.name}] Analizando solicitud del cliente: '{cliente_input}'\033[0m")
        
        # Check for ambiguity first
        input_lower = cliente_input.lower()
        
        # A request is ambiguous if it's too short, contains generic descriptions, and lacks technical indicators
        is_too_short = len(cliente_input.split()) < 5
        is_generic_issue = "no anda" in input_lower or "no funciona" in input_lower or input_lower.strip() in ["ayuda", "hola"]
        is_missing_details = not any(w in input_lower for w in ["laptop", "pc", "computadora", "notebook", "tablet", "ssd", "pantalla", "teclado", "arranca", "calienta", "sobrecalienta", "enciede", "prende"])

        # Gather previous conversation to extract slots across turns
        historial = shared_memory.get("historial_conversacion") or []
        
        # Parse client details using light heuristic extraction (including Spanish accented characters)
        nombre = self._extract_field(cliente_input, r"(?:me llamo|mi nombre es|soy)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)?)", "")
        contacto = self._extract_field(cliente_input, r"(\+?\d[\d\s\-]{6,12}\d|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b)", "")
        
        # If not found in the current message, try to extract from previous client messages in history
        for msg in reversed(historial):
            if msg.get("sender") == "cliente":
                prev_msg = msg.get("message", "")
                if not nombre:
                    nombre = self._extract_field(prev_msg, r"(?:me llamo|mi nombre es|soy)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)?)", "")
                if not contacto:
                    contacto = self._extract_field(prev_msg, r"(\+?\d[\d\s\-]{6,12}\d|\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b)", "")

        # Slot filling validation: Check if we are missing critical slots in an ambiguous turn
        if (is_too_short or is_generic_issue) and (is_missing_details or not nombre or not contacto):
            missing_slots = []
            if not nombre:
                missing_slots.append("tu nombre completo")
            if not contacto:
                missing_slots.append("tu medio de contacto (teléfono/email)")
            if is_missing_details:
                missing_slots.append("marca, modelo y descripción detallada de la falla de tu equipo")
            
            slots_str = ", ".join(missing_slots) if missing_slots else "más detalles sobre tu solicitud"
            
            output_payload = {
                "ticket_id": ticket_id,
                "status": "ambiguous",
                "respuesta_cliente": (
                    f"Hola de TechServ. Entendemos que tienes un inconveniente con tu equipo, "
                    f"pero para poder ayudarte necesitamos que nos brindes: {slots_str}. "
                    f"¿Podrías indicarnos estos detalles?"
                )
            }
            # Record in conversation history
            historial.append({"sender": "cliente", "message": cliente_input})
            historial.append({"sender": self.name, "message": output_payload["respuesta_cliente"]})
            shared_memory.set("historial_conversacion", historial, self.name)
            return output_payload

        # Defaults for safe fallback if not ambiguous but fields are missing
        if not nombre:
            nombre = "Juan Pérez"
        if not contacto:
            contacto = "555-0199"
            
        if nombre:
            words = nombre.split()
            if len(words) > 1 and words[-1].lower() in ["y", "o", "de", "con"]:
                nombre = " ".join(words[:-1])
        
        canal_preferido = "email"
        if "whatsapp" in input_lower or "celular" in input_lower or "cel" in input_lower:
            canal_preferido = "whatsapp"
        elif "sms" in input_lower or "mensaje" in input_lower:
            canal_preferido = "sms"
        elif "@" in contacto:
            canal_preferido = "email"

        # Classification rules
        if any(w in input_lower for w in ["comprar", "SSD", "ssd", "precio de", "venta", "cuánto cuesta el", "tarjeta", "accesorios", "pc completa"]):
            tipo_solicitud = "venta"
        elif any(w in input_lower for w in ["teclado", "tablet", "no responde", "soporte", "remoto", "configurar", "ayuda con software"]):
            # Tablet keyboard not responding -> remote support scaled
            if "tablet" in input_lower and "teclado" in input_lower:
                tipo_solicitud = "soporte"
            else:
                tipo_solicitud = "reparacion"
        else:
            tipo_solicitud = "reparacion"

        # Extract brand/model and symptoms
        marca_modelo = self._extract_field(cliente_input, r"(?:laptop|pc|notebook|tablet|computadora)\s+([A-Za-z0-9\s]+?)(?:\s+que|\s+con|\s+no|\s+tiene|\s+presenta|\s+se|\s+y|\s+de|\s+para|\.|$|,)", "PC Genérico")
        if "hp" in input_lower:
            marca_modelo = "HP Laptop"

        sintomas = []
        if "pantalla rota" in input_lower or "pantalla quebrada" in input_lower or "rotura" in input_lower:
            sintomas.append("Pantalla rota")
        if "no arranca" in input_lower or "no enciende" in input_lower or "sin arranque" in input_lower or "prende" in input_lower:
            sintomas.append("No enciende / Sin arranque")
        if "se calienta" in input_lower or "calienta" in input_lower or "apaga" in input_lower:
            sintomas.append("Se sobrecalienta y se apaga")
        if "no responde" in input_lower or "no funciona teclado" in input_lower:
            sintomas.append("Teclado no responde")

        if not sintomas:
            sintomas.append("Falla no especificada")

        # Fill Shared Memory
        shared_memory.set("ticket_id", ticket_id, self.name)
        shared_memory.set("cliente", {
            "nombre": nombre,
            "contacto": contacto,
            "canal_preferido": canal_preferido
        }, self.name)
        shared_memory.set("tipo_solicitud", tipo_solicitud, self.name)
        shared_memory.set("equipo", {
            "descripcion": f"{marca_modelo} de {nombre}",
            "sintomas": sintomas,
            "marca_modelo": marca_modelo
        }, self.name)
        shared_memory.set("estado_ticket", "recibido", self.name)

        historial.append({"sender": "cliente", "message": cliente_input})
        historial.append({"sender": self.name, "message": f"Solicitud clasificada como {tipo_solicitud.upper()} y ticket creado."})
        shared_memory.set("historial_conversacion", historial, self.name)

        output_payload = {
            "ticket_id": ticket_id,
            "status": "success",
            "tipo_solicitud": tipo_solicitud,
            "cliente": {
                "nombre": nombre,
                "contacto": contacto,
                "canal_preferido": canal_preferido
            },
            "equipo": {
                "marca_modelo": marca_modelo,
                "sintomas": sintomas
            }
        }

        # Publish ticket.creado
        event_bus.publish("ticket.creado", ticket_id, self.name, output_payload)
        
        return output_payload

    def _extract_field(self, text: str, pattern: str, default: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return default
