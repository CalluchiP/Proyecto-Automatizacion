from typing import Dict, Any, List
from antigravity.agents import SubAgent
from antigravity import SharedMemory, EventBus
from antigravity.tools import ClaudeCodeTools

class TechnicalDiagnosisAgent(SubAgent):
    def __init__(self):
        system_prompt = (
            "Eres el Agente Técnico del servicio de reparación de computadoras.\n"
            "Tu única responsabilidad es:\n"
            "1. Analizar los síntomas del equipo reportados en la Memoria Compartida.\n"
            "2. Generar un informe técnico detallado con posibles causas y solución recomendada.\n"
            "3. Listar las piezas requeridas para la reparación con código de parte y cantidad.\n"
            "4. Estimar costo total y tiempo de reparación en horas.\n"
            "5. Si el Almacén reporta falta de una pieza, proponer alternativas técnicas viables.\n"
            "6. Emitir el evento \"diagnostico.completado\" con el informe en formato JSON.\n"
            "No interactúes directamente con el cliente. Solo reporta al Orquestador.\n"
            "Usa bash tools de Claude Code para buscar fichas técnicas de equipos cuando sea necesario."
        )
        super().__init__(name="tecnico_diagnostico", system_prompt=system_prompt)
        self.tools = ClaudeCodeTools()

    def process(self, shared_memory: SharedMemory, event_bus: EventBus, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes technical diagnosis.
        Payload can contain: {"mediation_request": bool, "missing_part": str}
        """
        ticket_id = shared_memory.get("ticket_id")
        equipo = shared_memory.get("equipo") or {}
        sintomas = equipo.get("sintomas", [])
        marca_modelo = equipo.get("marca_modelo", "")
        
        print(f"\033[92m[{self.name}] Iniciando diagnóstico técnico para {marca_modelo}...\033[0m")
        
        # Check if we are in mediation mode (Warehouse reported missing parts)
        is_mediation = payload.get("mediation_request", False)
        
        if is_mediation:
            missing_part = payload.get("missing_part", "")
            print(f"\033[93m[{self.name} MEDIATION] Mediación activada por pieza faltante: {missing_part}\033[0m")
            
            # Check tech specs or compatible parts via mock web search
            search_res = self.tools.web_search(f"alternativa compatible {missing_part}")
            
            # Formulate alternative
            if "RAM DDR4 8GB" in missing_part:
                alternative_name = "Memoria RAM DDR4 16GB"
                alternative_code = "PART-RAM-DDR4-16G"
                print(f"\033[93m[{self.name} MEDIATION] Proponiendo pieza alternativa superior disponible: {alternative_name}\033[0m")
                
                # Get current diagnostic state
                current_diag = shared_memory.get("diagnostico") or {}
                piezas = current_diag.get("piezas_requeridas", [])
                
                # Replace the missing piece in the list
                new_piezas = []
                for p in piezas:
                    if p["nombre"] == missing_part:
                        new_piezas.append({
                            "nombre": alternative_name,
                            "codigo": alternative_code,
                            "cantidad": 1,
                            "precio_unitario": 80.0
                        })
                    else:
                        new_piezas.append(p)
                
                # Adjust cost
                costo_anterior = current_diag.get("costo_estimado", 0.0)
                # 8GB was $45, 16GB is $80. Difference is +$35.
                costo_nuevo = costo_anterior + 35.0
                
                diag_update = {
                    "informe": (
                        f"DIAGNÓSTICO ACTUALIZADO VÍA MEDIACIÓN: La memoria RAM DDR4 8GB original se encuentra agotada. "
                        f"Se propone instalar una unidad superior de 16GB DDR4 compatible. Esto mejorará la performance del equipo."
                    ),
                    "piezas_requeridas": new_piezas,
                    "costo_estimado": costo_nuevo,
                    "tiempo_estimado_horas": current_diag.get("tiempo_estimado_horas", 2)
                }
                
                shared_memory.set("diagnostico", diag_update, self.name)
                
                output = {
                    "ticket_id": ticket_id,
                    "status": "mediated",
                    "diagnostico": diag_update
                }
                
                # Emit event
                event_bus.publish("diagnostico.completado", ticket_id, self.name, output)
                return output
            else:
                # Generic fallback
                return {"ticket_id": ticket_id, "status": "failed_no_alternative"}

        # Normal Flow: Perform diagnosis based on symptoms
        diagnostico_data = {}
        sintomas_lower = [s.lower() for s in sintomas]
        
        # Consult tech specs using bash
        self.tools.bash(f"consultar_especificaciones '{marca_modelo}'")
        
        if "pantalla rota" in sintomas_lower:
            diagnostico_data = {
                "informe": "Pantalla LED con daño físico visible (quebrada). Requiere reemplazo completo del panel frontal.",
                "piezas_requeridas": [
                    {
                        "nombre": "Pantalla HP Laptop",
                        "codigo": "PART-HP-SCR-01",
                        "cantidad": 1,
                        "precio_unitario": 120.0
                    }
                ],
                "costo_estimado": 120.0 + 50.0, # Part + labor ($50)
                "tiempo_estimado_horas": 2
            }
        elif "no enciende / sin arranque" in sintomas_lower:
            # Dual failure (RAM + PSU)
            diagnostico_data = {
                "informe": (
                    "El equipo no responde a la pulsación de encendido. Pruebas de voltaje muestran falla en la fuente de poder "
                    "y problemas de lectura en los primeros sectores de memoria RAM. Se requiere cambiar Fuente de Poder y RAM DDR4 8GB."
                ),
                "piezas_requeridas": [
                    {
                        "nombre": "Fuente de Poder 600W",
                        "codigo": "PART-PSU-600W",
                        "cantidad": 1,
                        "precio_unitario": 65.0
                    },
                    {
                        "nombre": "Memoria RAM DDR4 8GB",
                        "codigo": "PART-RAM-DDR4-8G",
                        "cantidad": 1,
                        "precio_unitario": 45.0
                    }
                ],
                "costo_estimado": 65.0 + 45.0 + 75.0, # Parts + labor ($75)
                "tiempo_estimado_horas": 4
            }
        elif "se sobrecalienta y se apaga" in sintomas_lower:
            # Heat issues (Thermal paste + Fan)
            diagnostico_data = {
                "informe": (
                    "El CPU alcanza temperaturas críticas de 95°C bajo carga menor, activando el apagado de protección térmica. "
                    "El ventilador del procesador está obstruido y la pasta térmica original está totalmente seca. Se requiere limpieza, "
                    "reemplazo de pasta térmica y cambio de ventilador CPU."
                ),
                "piezas_requeridas": [
                    {
                        "nombre": "Pasta Térmica",
                        "codigo": "PART-THERM-PASTE",
                        "cantidad": 1,
                        "precio_unitario": 10.0
                    },
                    {
                        "nombre": "Ventilador CPU",
                        "codigo": "PART-CPU-FAN",
                        "cantidad": 1,
                        "precio_unitario": 25.0
                    }
                ],
                "costo_estimado": 10.0 + 25.0 + 40.0, # Parts + labor ($40)
                "tiempo_estimado_horas": 3
            }
        elif "teclado no responde" in sintomas_lower and ("tablet" in marca_modelo.lower() or any("tablet" in str(msg).lower() for msg in shared_memory.get("historial_conversacion", []))):
            # Support Remote
            diagnostico_data = {
                "informe": (
                    "Soporte remoto inicial: El teclado bluetooth de la tablet perdió sincronización tras actualización. "
                    "Se proveerán instrucciones para reinicio del hardware de red y re-sincronización."
                ),
                "piezas_requeridas": [],
                "costo_estimado": 0.0,
                "tiempo_estimado_horas": 1
            }
        else:
            diagnostico_data = {
                "informe": "Mantenimiento preventivo general y diagnóstico de software. No requiere piezas de hardware.",
                "piezas_requeridas": [],
                "costo_estimado": 40.0,
                "tiempo_estimado_horas": 1
            }

        # Update Shared Memory
        shared_memory.set("diagnostico", diagnostico_data, self.name)
        shared_memory.set("estado_ticket", "en_diagnostico", self.name)
        
        output = {
            "ticket_id": ticket_id,
            "status": "success",
            "diagnostico": diagnostico_data
        }
        
        # Publish event
        event_bus.publish("diagnostico.completado", ticket_id, self.name, output)
        
        return output
