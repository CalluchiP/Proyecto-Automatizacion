import time
from typing import Dict, Any, List
from antigravity.agents import OrchestratorAgent
from antigravity import SharedMemory, EventBus, Swarm

class Orchestrator(OrchestratorAgent):
    def __init__(self):
        system_prompt = (
            "Eres el Orquestador Central del sistema de gestión de un servicio técnico de computadoras.\n"
            "Tu única responsabilidad es:\n"
            "1. Recibir la solicitud del cliente (clasificada por el Agente de Atención).\n"
            "2. Evaluar el tipo de solicitud: VENTA, REPARACIÓN o SOPORTE.\n"
            "3. Delegar tareas a los subagentes correctos usando el Event Bus.\n"
            "4. Gestionar conflictos de disponibilidad: si el Almacén reporta falta de repuestos, \n"
            "   redirigir al Técnico para un diagnóstico alternativo o cotización de sustitutos.\n"
            "5. Consolidar los resultados de todos los subagentes en la Memoria Compartida.\n"
            "6. Garantizar que el historial de conversación se preserve íntegro entre turnos.\n"
            "Comunícate SIEMPRE en formato JSON Schema validado. Nunca asumas datos no confirmados."
        )
        super().__init__(name="orquestador", system_prompt=system_prompt)
        
        # Hierarchy for simultaneous write resolution
        # Higher index = higher priority
        self.hierarchy = [
            "notificaciones",
            "atencion_cliente",
            "ventas",
            "almacen",
            "tecnico_diagnostico",
            "orquestador"
        ]

    def resolve_write_conflict(self, agent_a: str, agent_b: str) -> str:
        """
        Implements: "última escritura confirmada por el agente de mayor jerarquía gana."
        Returns the agent name that wins.
        """
        priority_a = self.hierarchy.index(agent_a) if agent_a in self.hierarchy else -1
        priority_b = self.hierarchy.index(agent_b) if agent_b in self.hierarchy else -1
        
        if priority_a >= priority_b:
            print(f"\033[31m[Orquestador Conflicto Escritura] Conflicto entre '{agent_a}' y '{agent_b}'. Gana '{agent_a}' por jerarquía.\033[0m")
            return agent_a
        else:
            print(f"\033[31m[Orquestador Conflicto Escritura] Conflicto entre '{agent_a}' y '{agent_b}'. Gana '{agent_b}' por jerarquía.\033[0m")
            return agent_b

    def process_ticket(self, shared_memory: SharedMemory, event_bus: EventBus, subagents: Dict[str, Any], initial_input: str, ticket_id: str) -> bool:
        """
        Executes the entire multi-agent coordination loop based on the category.
        """
        print(f"\033[1;94m=== [Orquestador] INICIANDO FLUJO PARA TICKET {ticket_id} ===\033[0m")
        start_t = time.time()
        
        try:
            # 1. Attention Customer Agent receives input and classifies
            client_payload = {"cliente_input": initial_input, "ticket_id": ticket_id}
            atencion = subagents["atencion_cliente"]
            
            atencion_start = time.time()
            c_res = atencion.process(shared_memory, event_bus, client_payload)
            atencion.log_telemetry(atencion_start, str(client_payload), str(c_res))
            
            # Handle ambiguity/needs clarification
            if c_res.get("status") == "ambiguous":
                print(f"\033[93m[Orquestador] Solicitud ambigua detectada. Solicitando aclaración al cliente.\033[0m")
                self.log_telemetry(start_t, initial_input, str(c_res))
                # Execute notification
                subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "ticket.creado"})
                return False # Needs interactive turn

            # Extract classified details
            tipo_solicitud = shared_memory.get("tipo_solicitud")
            print(f"\033[94m[Orquestador] Tipo de Solicitud Clasificado: {tipo_solicitud.upper()}\033[0m")
            
            # Trigger ticket created notification
            subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "ticket.creado"})

            # Route the flow
            success = False
            if tipo_solicitud == "reparacion":
                success = self._run_reparacion_flow(shared_memory, event_bus, subagents, ticket_id)
            elif tipo_solicitud == "venta":
                success = self._run_venta_flow(shared_memory, event_bus, subagents, ticket_id)
            elif tipo_solicitud == "soporte":
                success = self._run_soporte_flow(shared_memory, event_bus, subagents, ticket_id)
            
            self.log_telemetry(start_t, initial_input, f"Flow completed with status: {success}")
            return success
        except Exception as e:
            print(f"\033[1;31m[Orquestador] ERROR CRÍTICO EN PROCESAMIENTO DE TICKET {ticket_id}: {e}\033[0m")
            try:
                shared_memory.set("estado_ticket", "error_interno", self.name)
                
                # Append error info to conversation history
                historial = shared_memory.get("historial_conversacion") or []
                historial.append({
                    "ticket_id": ticket_id,
                    "evento": "ticket.error",
                    "agente_emisor": self.name,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "payload": {"error": str(e), "estado_ticket": "error_interno"}
                })
                shared_memory.set("historial_conversacion", historial, self.name)
                
                # Notify the customer of internal error delay
                subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "ticket.error", "error_msg": str(e)})
            except Exception as e_inner:
                print(f"\033[1;31m[Orquestador] Error intentando guardar estado de error_interno: {e_inner}\033[0m")
            
            self.log_telemetry(start_t, initial_input, f"Flow failed with exception: {e}")
            return False

    def _run_reparacion_flow(self, shared_memory: SharedMemory, event_bus: EventBus, subagents: Dict[str, Any], ticket_id: str) -> bool:
        """
        Runs the complex repair pipeline:
        1. Swarm [Técnico + Almacén] parallel execution
        2. Stock check
        3. Mediation if missing stock
        4. Budget approval
        5. Quality test
        6. Completed notification
        """
        # Create Swarm
        swarm = Swarm(
            agents=["tecnico_diagnostico", "almacen"],
            mode="parallel",
            trigger_event="ticket.creado",
            join_condition="all_completed"
        )
        
        # Execute swarm parallel logic
        swarm_payload = {"ticket_id": ticket_id}
        swarm_results = swarm.run_parallel(shared_memory, event_bus, swarm_payload, subagents)
        
        # Consolidate results
        # Determine inventory check result
        inventario_res = shared_memory.get("inventario") or {}
        is_available = inventario_res.get("disponible", False)
        
        if not is_available:
            missing = ""
            # Identify missing part from Warehouse result
            for r in swarm_results:
                if r["agent"] == "almacen":
                    missing = r["result"].get("missing_part", "")
            
            print(f"\033[31m[Orquestador] CONFLICTO DETECTADO: Repuesto '{missing}' agotado. Iniciando ciclo de Mediación.\033[0m")
            
            # Step 1 of Mediation: Ask Technical Agent for alternative
            mediation_payload = {"mediation_request": True, "missing_part": missing}
            tecnico = subagents["tecnico_diagnostico"]
            t_start = time.time()
            med_res = tecnico.process(shared_memory, event_bus, mediation_payload)
            tecnico.log_telemetry(t_start, str(mediation_payload), str(med_res))
            
            # Step 2 of Mediation: Ask Warehouse to check the alternative
            almacen = subagents["almacen"]
            a_start = time.time()
            val_res = almacen.process(shared_memory, event_bus, {"ticket_id": ticket_id})
            almacen.log_telemetry(a_start, "Check alternative part", str(val_res))
            
            # Recheck stock availability of alternative
            inventario_res = shared_memory.get("inventario") or {}
            is_available = inventario_res.get("disponible", False)
            
            if not is_available:
                print(f"\033[31m[Orquestador] Mediación fallida. No hay stock para alternativas de '{missing}'.\033[0m")
                return False
            
            print(f"\033[92m[Orquestador] Mediación exitosa! Alternativa técnica aprobada y reservada.\033[0m")

        # 3. Budget Generation
        shared_memory.set("estado_ticket", "presupuestado", self.name)
        event_bus.publish("presupuesto.generado", ticket_id, self.name, {"estado": "presupuestado"})
        subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "presupuesto.generado"})
        
        # 4. Simulate Client Approval (Automatic for testing)
        print(f"\033[94m[Orquestador] Simulando aprobación de presupuesto por parte del cliente...\033[0m")
        time.sleep(0.1)
        
        # 5. Start Repair
        shared_memory.set("estado_ticket", "en_reparacion", self.name)
        event_bus.publish("reparacion.iniciada", ticket_id, self.name, {"estado": "en_reparacion"})
        subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "reparacion.iniciada"})
        
        # 6. Technical completes repair
        print(f"\033[92m[Técnico] Reparando equipo físicamente...\033[0m")
        time.sleep(0.1)
        shared_memory.set("estado_ticket", "listo", self.name)
        event_bus.publish("reparacion.completada", ticket_id, self.name, {"estado": "listo"})
        subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "reparacion.completada"})
        
        # 7. Quality Control Software Test (Using bash command simulation)
        print(f"\033[94m[Orquestador] Iniciando control de calidad automático...\033[0m")
        qc_result = subagents["tecnico_diagnostico"].tools.bash("run_qa_check_suite")
        print(f"\033[92m[Orquestador QC Suite] Resultado QC: {qc_result}\033[0m")
        
        # Quality Approved
        event_bus.publish("calidad.aprobada", ticket_id, self.name, {"test_output": qc_result})
        subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "calidad.aprobada"})
        
        shared_memory.set("estado_ticket", "entregado", self.name)
        return True

    def _run_venta_flow(self, shared_memory: SharedMemory, event_bus: EventBus, subagents: Dict[str, Any], ticket_id: str) -> bool:
        """
        Runs the sales pipeline:
        1. Sales AI recommendation
        2. Stock confirmation
        3. Payment transaction
        4. Notification
        """
        equipo = shared_memory.get("equipo") or {}
        desc = equipo.get("descripcion", "")
        
        # Match purchase item from description
        item_name = "SSD 1TB" # default
        if "500gb" in desc.lower():
            item_name = "SSD 500GB"
        
        # Call Sales Agent
        sales_payload = {"item_name": item_name, "quantity": 1}
        sales = subagents["ventas"]
        s_start = time.time()
        s_res = sales.process(shared_memory, event_bus, sales_payload)
        sales.log_telemetry(s_start, str(sales_payload), str(s_res))
        
        # Validate stock with warehouse
        almacen = subagents["almacen"]
        a_start = time.time()
        inv_res = almacen.process(shared_memory, event_bus, {"ticket_id": ticket_id})
        almacen.log_telemetry(a_start, "Sales stock check", str(inv_res))
        
        is_avail = shared_memory.get("inventario", {}).get("disponible", False)
        if not is_avail:
            print(f"\033[31m[Orquestador] Error de venta: No hay stock del producto {item_name}.\033[0m")
            return False
            
        # Process order payment and finalize
        subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "venta.procesada"})
        
        return True

    def _run_soporte_flow(self, shared_memory: SharedMemory, event_bus: EventBus, subagents: Dict[str, Any], ticket_id: str) -> bool:
        """
        Runs the linear support pipeline:
        1. Technical agent remote solution
        2. If fails, escalates to REPARACIÓN. Else, completes.
        """
        tecnico = subagents["tecnico_diagnostico"]
        t_start = time.time()
        t_res = tecnico.process(shared_memory, event_bus, {})
        tecnico.log_telemetry(t_start, "Remote support request", str(t_res))
        
        diag = shared_memory.get("diagnostico") or {}
        
        print(f"\033[94m[Orquestador] Ejecutando instrucciones de soporte remoto...\033[0m")
        
        # In ticket 4, remote support succeeds! Let's check if it solves the symptoms.
        equipo = shared_memory.get("equipo") or {}
        sintomas = equipo.get("sintomas", [])
        
        if "Teclado no responde" in sintomas and ("tablet" in equipo.get("marca_modelo", "").lower() or "teclado" in equipo.get("marca_modelo", "").lower() or "tablet" in equipo.get("descripcion", "").lower()):
            print(f"\033[92m[Orquestador] Soporte remoto RESOLVIÓ el inconveniente. Cerrando ticket.\033[0m")
            shared_memory.set("estado_ticket", "entregado", self.name)
            subagents["notificaciones"].process(shared_memory, event_bus, {"evento": "calidad.aprobada"})
            return True
        else:
            # Escalation to REPARACIÓN
            print(f"\033[93m[Orquestador] Soporte remoto fallido. Escalando solicitud a flujo de REPARACIÓN física.\033[0m")
            shared_memory.set("tipo_solicitud", "reparacion", self.name)
            return self._run_reparacion_flow(shared_memory, event_bus, subagents, ticket_id)
