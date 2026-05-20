import os
import sys
import unittest

# Ensure base path is in path
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

class TestFlujoReparacion(unittest.TestCase):
    def setUp(self):
        reset_inventory()
        self.shared_memory = get_shared_memory()
        self.event_bus = get_event_bus()
        self.orquestador = Orchestrator()
        
        self.subagents = {
            "atencion_cliente": CustomerServiceAgent(),
            "tecnico_diagnostico": TechnicalDiagnosisAgent(),
            "ventas": None, # Not needed here
            "almacen": WarehouseAgent(),
            "notificaciones": NotificationsAgent()
        }

    def test_reparacion_pantalla_disponible(self):
        """
        Caso 1: Laptop HP con pantalla rota - Repuesto disponible en almacén
        """
        ticket_id = "TKT-TEST-001"
        client_input = "Hola, soy Carlos Pérez, mi cel es +5491133334444 y prefiero whatsapp. Mi laptop HP tiene la pantalla rota."
        
        # Initialize memory
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
        self.assertEqual(self.shared_memory.get("tipo_solicitud"), "reparacion")
        
        cliente = self.shared_memory.get("cliente")
        self.assertEqual(cliente["nombre"], "Carlos Pérez")
        self.assertEqual(cliente["canal_preferido"], "whatsapp")
        
        equipo = self.shared_memory.get("equipo")
        self.assertIn("HP Laptop", equipo["marca_modelo"])
        
        diagnostico = self.shared_memory.get("diagnostico")
        self.assertIn("Pantalla HP Laptop", [p["nombre"] for p in diagnostico["piezas_requeridas"]])
        self.assertEqual(diagnostico["costo_estimado"], 170.0) # $120 part + $50 labor

    def test_reparacion_ram_agotada_mediacion(self):
        """
        Caso 2: PC gamer sin arranque - RAM faltante - Mediación a RAM 16GB
        """
        ticket_id = "TKT-TEST-002"
        client_input = "Buenas, soy Sofía Gómez, mi email es sofia@gmail.com, celular +5491155556666, prefiero sms. Mi PC gamer de escritorio no arranca para nada."
        
        # Initialize memory
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
        
        diagnostico = self.shared_memory.get("diagnostico")
        # Assert that the proposed parts list has 16GB RAM alternative instead of 8GB
        partes = [p["nombre"] for p in diagnostico["piezas_requeridas"]]
        self.assertIn("Fuente de Poder 600W", partes)
        self.assertIn("Memoria RAM DDR4 16GB", partes)
        self.assertNotIn("Memoria RAM DDR4 8GB", partes) # Standard RAM out of stock is not in final order!
        
        # Original cost: RAM 8G ($45) + PSU ($65) + labor ($75) = $185
        # Mediated cost: RAM 16G ($80) + PSU ($65) + labor ($75) = $220
        self.assertEqual(diagnostico["costo_estimado"], 220.0)

if __name__ == "__main__":
    unittest.main()
