import os
import json
import time
from typing import Dict, Any, List
from antigravity.agents import SubAgent
from antigravity import SharedMemory, EventBus

class WarehouseAgent(SubAgent):
    def __init__(self):
        system_prompt = (
            "Eres el Agente de Almacén del servicio técnico.\n"
            "Tu única responsabilidad es:\n"
            "1. Verificar disponibilidad de los repuestos solicitados por el Agente Técnico o Ventas.\n"
            "2. Actualizar el inventario en Memoria Compartida al confirmar o descontar unidades.\n"
            "3. Si una pieza no está disponible, generar una orden de aprovisionamiento automática.\n"
            "4. Emitir el evento \"inventario.verificado\" con la lista de piezas disponibles o pedidas.\n"
            "No diagnostiques equipos ni atiendas clientes. Solo gestiona stock.\n"
            "Usa herramientas de edición de archivos de Claude Code para mantener el registro de inventario."
        )
        super().__init__(name="almacen", system_prompt=system_prompt)
        # Determine absolute path to inventario.json to ensure robustness
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.inventory_path = os.path.join(base_dir, "data", "inventario.json")

    def _acquire_lock(self):
        lock_path = self.inventory_path + ".lock"
        start_time = time.time()
        # Wait up to 5 seconds to acquire lock
        while True:
            try:
                # O_CREAT | O_EXCL ensures atomic lock creation at OS level
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                if time.time() - start_time > 5.0:
                    print(f"\033[91m[{self.name}] Tiempo de espera agotado para adquirir bloqueo del inventario. Continuando de todos modos...\033[0m")
                    break
                time.sleep(0.05)

    def _release_lock(self):
        lock_path = self.inventory_path + ".lock"
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
        except Exception:
            pass

    def process(self, shared_memory: SharedMemory, event_bus: EventBus, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes stock verification and reservations.
        """
        self._acquire_lock()
        try:
            ticket_id = shared_memory.get("ticket_id")
            diagnostico = shared_memory.get("diagnostico") or {}
            piezas_requeridas = diagnostico.get("piezas_requeridas", [])
            
            print(f"\033[92m[{self.name}] Verificando stock para ticket {ticket_id}...\033[0m")
            
            # Load current database
            inventory = self._load_inventory()
            
            disponible_total = True
            piezas_confirmadas = []
            orden_aprovisionamiento = ""
            missing_part = ""

            # Verify stock for each required part
            for pieza in piezas_requeridas:
                nombre = pieza["nombre"]
                cantidad = pieza.get("cantidad", 1)
                
                if nombre in inventory:
                    stock_actual = inventory[nombre]["stock"]
                    print(f"\033[92m[{self.name}] -> {nombre}: Stock actual = {stock_actual}, Solicitado = {cantidad}\033[0m")
                    
                    if stock_actual >= cantidad:
                        # Piece available. Reserve it (temporarily decrement stock)
                        inventory[nombre]["stock"] = stock_actual - cantidad
                        piezas_confirmadas.append(nombre)
                    else:
                        # Out of stock!
                        disponible_total = False
                        missing_part = nombre
                        print(f"\033[91m[{self.name} ALERTA] Stock insuficiente para: {nombre}!\033[0m")
                else:
                    # Part not in inventory database
                    disponible_total = False
                    missing_part = nombre
                    print(f"\033[91m[{self.name} ALERTA] Repuesto no registrado en la base de datos: {nombre}!\033[0m")

            if not disponible_total:
                # Generate automatic procurement order
                orden_aprovisionamiento = f"ORD-PROV-{ticket_id.split('-')[-1]}-01"
                print(f"\033[93m[{self.name}] Generando orden de aprovisionamiento automática: {orden_aprovisionamiento}\033[0m")
                # Don't save changes to inventory yet as we have a missing part that may block the repair or require alternatives
            else:
                # Save the updated stock in database
                self._save_inventory(inventory)
                print(f"\033[92m[{self.name}] Stock confirmado y reservado en inventario.json.\033[0m")

            # Save to Shared Memory
            inventario_state = {
                "disponible": disponible_total,
                "piezas_confirmadas": piezas_confirmadas,
                "orden_aprovisionamiento": orden_aprovisionamiento
            }
            
            shared_memory.set("inventario", inventario_state, self.name)
            
            output = {
                "ticket_id": ticket_id,
                "status": "success" if disponible_total else "out_of_stock",
                "inventario": inventario_state,
                "missing_part": missing_part
            }
            
            # Publish event
            event_bus.publish("inventario.verificado", ticket_id, self.name, output)
            
            return output
        finally:
            self._release_lock()

    def _load_inventory(self) -> Dict[str, Any]:
        if not os.path.exists(self.inventory_path):
            print(f"\033[91m[Warehouse Error] No se encontró el archivo de inventario en {self.inventory_path}!\033[0m")
            return {}
        try:
            with open(self.inventory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"\033[91m[Warehouse Error] Error al leer archivo: {str(e)}\033[0m")
            return {}

    def _save_inventory(self, data: Dict[str, Any]):
        try:
            with open(self.inventory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"\033[91m[Warehouse Error] Error al escribir en inventario.json: {str(e)}\033[0m")
