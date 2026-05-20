import os
import sys
import json
import time
import mimetypes
from urllib.parse import parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Ensure current directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from antigravity import SharedMemory, EventBus
from antigravity.engine import TelemetryEngine
from shared.memory import get_shared_memory
from shared.event_bus import get_event_bus
from agents import (
    Orchestrator,
    CustomerServiceAgent,
    TechnicalDiagnosisAgent,
    SalesAgent,
    WarehouseAgent,
    NotificationsAgent
)

# In-memory session store to preserve shared memory state between interactive turns
SESSIONS = {}

# Reset stock utility for simulation demos
def reset_inventory_data():
    inv_file = os.path.join(current_dir, "data", "inventario.json")
    default_stock = {
        "PART-SCREEN-HP": {
            "nombre": "Pantalla HP Laptop 15",
            "stock": 5,
            "precio": 120.0
        },
        "PART-RAM-8G": {
            "nombre": "Memoria RAM DDR4 8GB",
            "stock": 0,
            "precio": 45.0
        },
        "PART-RAM-16G": {
            "nombre": "Memoria RAM DDR4 16GB",
            "stock": 3,
            "precio": 80.0
        },
        "PART-PSU-600": {
            "nombre": "Fuente de Poder 600W",
            "stock": 2,
            "precio": 65.0
        },
        "PART-SSD-1TB": {
            "nombre": "SSD 1TB",
            "stock": 5,
            "precio": 110.0
        },
        "PART-SSD-500": {
            "nombre": "SSD 500GB",
            "stock": 10,
            "precio": 60.0
        },
        "PART-THERMAL-PASTE": {
            "nombre": "Pasta Térmica",
            "stock": 15,
            "precio": 10.0
        },
        "PART-FAN-CPU": {
            "nombre": "Ventilador CPU",
            "stock": 4,
            "precio": 25.0
        }
    }
    with open(inv_file, "w", encoding="utf-8") as f:
        json.dump(default_stock, f, indent=2, ensure_ascii=False)


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # 1. API: Get stock details
        if path == "/api/inventory":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            inv_file = os.path.join(current_dir, "data", "inventario.json")
            if os.path.exists(inv_file):
                with open(inv_file, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write(json.dumps({}).encode("utf-8"))
            return
            
        # 2. Serve static files
        if path == "/":
            path = "/index.html"
            
        # Clean leading slashes
        clean_path = path.lstrip("/")
        file_path = os.path.join(current_dir, "dashboard", clean_path)
        
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            mime_type, _ = mimetypes.guess_type(file_path)
            self.send_response(200)
            self.send_header("Content-Type", mime_type or "application/octet-stream")
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Enable CORS
        if path == "/api/simulate":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            
            ticket_id = data.get("ticket_id", f"TKT-WEB-{int(time.time())}")
            client_input = data.get("client_input", "").strip()
            reset_stock = data.get("reset_stock", False)
            
            if reset_stock:
                reset_inventory_data()
                SESSIONS.clear()
            
            # Setup session
            is_new_session = ticket_id not in SESSIONS
            if is_new_session:
                shared_memory = get_shared_memory()
                # Initialize basic shared state
                shared_memory.initialize_state({
                    "ticket_id": ticket_id,
                    "cliente": {},
                    "tipo_solicitud": "",
                    "equipo": {},
                    "diagnostico": {},
                    "inventario": {},
                    "estado_ticket": "recibido",
                    "historial_conversacion": []
                })
                SESSIONS[ticket_id] = shared_memory
            else:
                shared_memory = SESSIONS[ticket_id]
                
            # Intercept published events to show in the visual console
            event_bus = get_event_bus()
            captured_events = []
            
            def event_listener(mcp_message):
                captured_events.append(mcp_message)
                
            # Subscribe to all events
            for ev in ["ticket.creado", "diagnostico.completado", "presupuesto.generado", 
                       "inventario.verificado", "reparacion.iniciada", "reparacion.completada", 
                       "calidad.aprobada", "venta.procesada", "ticket.error"]:
                event_bus.subscribe(ev, event_listener)

            # Reset and register Telemetry metrics
            telemetry = TelemetryEngine()
            telemetry.reset()
            
            orquestador = Orchestrator()
            atencion_cliente = CustomerServiceAgent()
            tecnico_diagnostico = TechnicalDiagnosisAgent()
            ventas = SalesAgent()
            almacen = WarehouseAgent()
            notificaciones = NotificationsAgent()
            
            telemetry.register_agent("orquestador", orquestador)
            telemetry.register_agent("atencion_cliente", atencion_cliente)
            telemetry.register_agent("tecnico_diagnostico", tecnico_diagnostico)
            telemetry.register_agent("ventas", ventas)
            telemetry.register_agent("almacen", almacen)
            telemetry.register_agent("notificaciones", notificaciones)
            
            subagents = {
                "atencion_cliente": atencion_cliente,
                "tecnico_diagnostico": tecnico_diagnostico,
                "ventas": ventas,
                "almacen": almacen,
                "notificaciones": notificaciones
            }
            
            # Execute simulation
            start_time = time.time()
            success = orquestador.process_ticket(
                shared_memory, 
                event_bus, 
                subagents, 
                client_input, 
                ticket_id
            )
            elapsed_time_ms = round((time.time() - start_time) * 1000, 2)
            
            # Record ticket result for final statistics
            telemetry.record_ticket_result(success)
            summary = telemetry.get_summary()
            
            # Prepare response payload
            response_payload = {
                "ticket_id": ticket_id,
                "success": success,
                "state": {
                    "ticket_id": shared_memory.get("ticket_id"),
                    "cliente": shared_memory.get("cliente"),
                    "tipo_solicitud": shared_memory.get("tipo_solicitud"),
                    "equipo": shared_memory.get("equipo"),
                    "diagnostico": shared_memory.get("diagnostico"),
                    "inventario": shared_memory.get("inventario"),
                    "estado_ticket": shared_memory.get("estado_ticket"),
                    "historial_conversacion": shared_memory.get("historial_conversacion")
                },
                "events": captured_events,
                "memory_history": shared_memory.history, # History of all variable updates
                "telemetry": summary,
                "server_duration_ms": elapsed_time_ms
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload, ensure_ascii=False).encode("utf-8"))
            return
            
        self.send_response(404)
        self.end_headers()

    # Enable preflight CORS checks
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run(server_class=HTTPServer, handler_class=DashboardHandler, port=8000):
    # Ensure mimetypes are registered for CSS and JS files
    mimetypes.init()
    
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print("\033[1;92m" + "="*80)
    print(f" SERVIDOR TECHSERV INICIADO EXITOSAMENTE EN: http://localhost:{port}")
    print(" Abre esta URL en tu navegador para ver la interfaz gráfica interactiva.")
    print("="*80 + "\033[0m")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[91mServidor detenido por el usuario.\033[0m")
        httpd.server_close()


if __name__ == "__main__":
    # Ensure inventory has fresh stock on start
    reset_inventory_data()
    run()
