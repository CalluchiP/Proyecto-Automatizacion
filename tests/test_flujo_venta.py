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
    SalesAgent,
    WarehouseAgent,
    NotificationsAgent
)

class TestFlujoVenta(unittest.TestCase):
    def setUp(self):
        reset_inventory()
        self.shared_memory = get_shared_memory()
        self.event_bus = get_event_bus()
        self.orquestador = Orchestrator()
        
        self.subagents = {
            "atencion_cliente": CustomerServiceAgent(),
            "tecnico_diagnostico": None, # Not needed in sales
            "ventas": SalesAgent(),
            "almacen": WarehouseAgent(),
            "notificaciones": NotificationsAgent()
        }

    def test_compra_ssd_disponible(self):
        """
        Caso 3: Compra de SSD 1TB - Disponible en almacén y recomendaciones de IA aplicadas
        """
        ticket_id = "TKT-TEST-003"
        client_input = "Hola, me llamo Alejandro Ruiz, contacto al@gmail.com, prefiero email. Quiero comprar un SSD 1TB para actualizar mi equipo."
        
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
        self.assertEqual(self.shared_memory.get("tipo_solicitud"), "venta")
        
        # Check sales recommendation
        diagnostico = self.shared_memory.get("diagnostico")
        self.assertIn("Venta de SSD 1TB procesada", diagnostico["informe"])
        
        # Base: $110. Discount 10% = $11. Final cost: $99.
        self.assertEqual(diagnostico["costo_estimado"], 99.0)
        
        inventario = self.shared_memory.get("inventario")
        self.assertTrue(inventario["disponible"])
        self.assertIn("SSD 1TB", inventario["piezas_confirmadas"])

if __name__ == "__main__":
    unittest.main()
