import os
import sys
import unittest

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from antigravity import SharedMemory, EventBus
from tests import reset_inventory
from shared.memory import get_shared_memory
from shared.event_bus import get_event_bus
from agents import (
    Orchestrator,
    CustomerServiceAgent,
    TechnicalDiagnosisAgent,
    WarehouseAgent,
    NotificationsAgent
)

class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        reset_inventory()
        self.shared_memory = get_shared_memory()
        self.event_bus = get_event_bus()
        self.orquestador = Orchestrator()
        
        self.subagents = {
            "atencion_cliente": CustomerServiceAgent(),
            "tecnico_diagnostico": TechnicalDiagnosisAgent(),
            "ventas": None,
            "almacen": WarehouseAgent(),
            "notificaciones": NotificationsAgent()
        }

    def test_soporte_remoto_exitoso(self):
        """
        Caso 4: Tablet con teclado que no responde bluetooth - Soporte remoto resuelve
        """
        ticket_id = "TKT-TEST-004"
        client_input = "Hola, soy Mateo Torres, celular +5491188887777, prefiero whatsapp. Mi tablet con teclado no responde bluetooth."
        
        self.shared_memory.initialize_state({
            "ticket_id": ticket_id,
            "cliente": {},
            "tipo_solicitud": "",
            "equipo": {},
            "diagnostico": {},
            "inventario": {},
            "estado_ticket": "recibido",
            "historial_conversacion": []
        })

        success = self.orquestador.process_ticket(
            self.shared_memory, 
            self.event_bus, 
            self.subagents, 
            client_input, 
            ticket_id
        )

        self.assertTrue(success)
        self.assertEqual(self.shared_memory.get("estado_ticket"), "entregado")
        self.assertEqual(self.shared_memory.get("tipo_solicitud"), "soporte")
        
        diagnostico = self.shared_memory.get("diagnostico")
        self.assertIn("Soporte remoto", diagnostico["informe"])
        self.assertEqual(len(diagnostico["piezas_requeridas"]), 0) # No parts needed
        self.assertEqual(diagnostico["costo_estimado"], 0.0) # Free remote support!

    def test_input_ambiguo_aclaracion_interactiva(self):
        """
        Caso 5: Input ambiguo 'mi compu no anda'.
        Paso 1: Agente Atención solicita aclaración.
        Paso 2: Cliente responde aclarando y se ejecuta flujo de Reparación por Sobrecalentamiento.
        """
        ticket_id = "TKT-TEST-005"
        first_input = "Hola, me llamo Lucía y mi compu no anda."
        clarification_input = "Es una Laptop Dell Inspiron, se calienta demasiado y se apaga a los 10 minutos de uso. Mi contacto es lucia@outlook.com y prefiero email."

        self.shared_memory.initialize_state({
            "ticket_id": ticket_id,
            "cliente": {},
            "tipo_solicitud": "",
            "equipo": {},
            "diagnostico": {},
            "inventario": {},
            "estado_ticket": "recibido",
            "historial_conversacion": []
        })

        # Step 1: Process ambiguous request
        success_first = self.orquestador.process_ticket(
            self.shared_memory, 
            self.event_bus, 
            self.subagents, 
            first_input, 
            ticket_id
        )

        # Should return False as it requires more interaction
        self.assertFalse(success_first)
        self.assertEqual(self.shared_memory.get("estado_ticket"), "recibido")
        
        historial = self.shared_memory.get("historial_conversacion")
        self.assertIn("necesitamos que nos brindes", str(historial))

        # Step 2: Client provides clarification input
        success_second = self.orquestador.process_ticket(
            self.shared_memory, 
            self.event_bus, 
            self.subagents, 
            clarification_input, 
            ticket_id
        )

        # Should complete repair flow successfully
        self.assertTrue(success_second)
        self.assertEqual(self.shared_memory.get("estado_ticket"), "entregado")
        self.assertEqual(self.shared_memory.get("tipo_solicitud"), "reparacion")
        
        cliente = self.shared_memory.get("cliente")
        self.assertEqual(cliente["nombre"], "Lucía")
        self.assertEqual(cliente["canal_preferido"], "email")
        
        diagnostico = self.shared_memory.get("diagnostico")
        partes = [p["nombre"] for p in diagnostico["piezas_requeridas"]]
        self.assertIn("Pasta Térmica", partes)
        self.assertIn("Ventilador CPU", partes)
        
        # Parts cost: Pasta Termica ($10) + Ventilador CPU ($25) + labor ($40) = $75
        self.assertEqual(diagnostico["costo_estimado"], 75.0)

if __name__ == "__main__":
    unittest.main()
