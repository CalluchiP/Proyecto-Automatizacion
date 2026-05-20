import os
import json

def reset_inventory():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inventory_path = os.path.join(base_dir, "data", "inventario.json")
    
    initial_inventory = {
      "Pantalla HP Laptop": {
        "codigo": "PART-HP-SCR-01",
        "stock": 5,
        "precio": 120.0
      },
      "Memoria RAM DDR4 8GB": {
        "codigo": "PART-RAM-DDR4-8G",
        "stock": 0,
        "precio": 45.0
      },
      "Memoria RAM DDR4 16GB": {
        "codigo": "PART-RAM-DDR4-16G",
        "stock": 5,
        "precio": 80.0
      },
      "Fuente de Poder 600W": {
        "codigo": "PART-PSU-600W",
        "stock": 5,
        "precio": 65.0
      },
      "SSD 1TB": {
        "codigo": "PART-SSD-1TB",
        "stock": 5,
        "precio": 110.0
      },
      "SSD 500GB": {
        "codigo": "PART-SSD-500G",
        "stock": 12,
        "precio": 60.0
      },
      "Teclado Tablet": {
        "codigo": "PART-TAB-KB-01",
        "stock": 2,
        "precio": 40.0
      },
      "Pasta Térmica": {
        "codigo": "PART-THERM-PASTE",
        "stock": 20,
        "precio": 10.0
      },
      "Ventilador CPU": {
        "codigo": "PART-CPU-FAN",
        "stock": 5,
        "precio": 25.0
      }
    }
    
    os.makedirs(os.path.dirname(inventory_path), exist_ok=True)
    with open(inventory_path, "w", encoding="utf-8") as f:
        json.dump(initial_inventory, f, indent=2, ensure_ascii=False)
