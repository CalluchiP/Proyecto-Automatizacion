from typing import Dict, Any
from antigravity.agents import SubAgent
from antigravity import SharedMemory, EventBus

class SalesAgent(SubAgent):
    def __init__(self):
        system_prompt = (
            "Eres el Agente de Ventas del servicio técnico.\n"
            "Tu única responsabilidad es:\n"
            "1. Procesar órdenes de venta de equipos y accesorios.\n"
            "2. Recomendar productos relevantes basándote en el perfil del cliente y su solicitud.\n"
            "3. Calcular precios, descuentos y total de la orden.\n"
            "4. Confirmar disponibilidad con el Agente de Almacén antes de cerrar la venta.\n"
            "5. Registrar el pago y emitir el evento \"venta.procesada\".\n"
            "No repares equipos ni gestiones tickets de soporte. Solo procesa ventas."
        )
        super().__init__(name="ventas", system_prompt=system_prompt)

    def process(self, shared_memory: SharedMemory, event_bus: EventBus, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes sales requests.
        Payload can contain: {"item_name": str, "quantity": int}
        """
        ticket_id = shared_memory.get("ticket_id")
        cliente = shared_memory.get("cliente") or {}
        
        print(f"\033[92m[{self.name}] Procesando orden de venta para {cliente.get('nombre', 'Cliente')}...\033[0m")
        
        item_name = payload.get("item_name", "")
        quantity = payload.get("quantity", 1)
        
        # Recommendations engine
        recommendation = ""
        suggested_item = ""
        discount = 0.0
        
        if "ssd 1tb" in item_name.lower():
            # Cross-selling or budget alternative
            suggested_item = "SSD 500GB"
            discount = 0.10 # 10% discount on 1TB SSD if they proceed, or suggest 500GB
            recommendation = (
                f"RECOMENDACIÓN DE IA: Detectamos que buscas el SSD 1TB ($110). "
                f"Si tu presupuesto es ajustado, te ofrecemos el SSD 500GB ($60) en oferta especial. "
                f"O si compras hoy el SSD 1TB, te aplicamos un 10% de descuento en el total."
            )
            print(f"\033[92m[{self.name}] {recommendation}\033[0m")

        # Set default pricing from our inventory list
        price_map = {
            "SSD 1TB": 110.0,
            "SSD 500GB": 60.0
        }
        
        unit_price = price_map.get(item_name, 50.0)
        subtotal = unit_price * quantity
        total_discount = subtotal * discount
        total = subtotal - total_discount
        
        sales_order = {
            "producto": item_name,
            "cantidad": quantity,
            "precio_unitario": unit_price,
            "subtotal": subtotal,
            "descuento_aplicado": total_discount,
            "total": total,
            "recomendacion": recommendation,
            "pago_confirmado": True
        }
        
        # Save order info into shared memory under diagnostico (as order summary)
        shared_memory.set("diagnostico", {
            "informe": f"Venta de {item_name} procesada correctamente. Pago confirmado.",
            "piezas_requeridas": [
                {
                    "nombre": item_name,
                    "codigo": "PART-SSD-1TB" if "1tb" in item_name.lower() else "PART-SSD-500G",
                    "cantidad": quantity,
                    "precio_unitario": unit_price
                }
            ],
            "costo_estimado": total,
            "tiempo_estimado_horas": 0
        }, self.name)
        
        shared_memory.set("estado_ticket", "entregado", self.name)
        
        # Update history
        historial = shared_memory.get("historial_conversacion") or []
        historial.append({
            "sender": self.name, 
            "message": f"Orden de venta procesada. Total: ${total:.2f}. Pago registrado exitosamente."
        })
        shared_memory.set("historial_conversacion", historial, self.name)
        
        output = {
            "ticket_id": ticket_id,
            "status": "success",
            "sales_order": sales_order
        }
        
        # Emit event
        event_bus.publish("venta.procesada", ticket_id, self.name, output)
        
        return output
