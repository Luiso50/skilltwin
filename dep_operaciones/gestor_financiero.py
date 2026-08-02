import os
import json
from datetime import datetime, timedelta
import threading

# Soporte para JSON (legacy) y SQLite (nuevo)
USE_SQLITE = os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"

DB_FINANZAS = os.path.join(os.path.dirname(__file__), "finanzas_db.json")
db_lock = threading.RLock()

if USE_SQLITE:
    try:
        from dep_operaciones.database import cargar_flujo_caja as db_cargar_flujo_caja
        from dep_operaciones.database import guardar_flujo_caja as db_guardar_flujo_caja
        from dep_operaciones.database import cargar_cuentas_cobrar as db_cargar_cuentas_cobrar
        from dep_operaciones.database import cargar_cuentas_pagar as db_cargar_cuentas_pagar
        from dep_operaciones.database import get_connection
        from dep_operaciones.database import init_database
        init_database()
    except ImportError:
        USE_SQLITE = False


def inicializar_finanzas():
    """Crea la base de datos financiera si no existe, con datos iniciales realistas."""
    if USE_SQLITE:
        # Verificar si hay datos
        flujo = db_cargar_flujo_caja()
        if flujo:
            return  # Ya hay datos
        
        # Crear datos iniciales
        hoy = datetime.now()
        db_guardar_flujo_caja("2026-05", 1500.0, 1420.0, 600.0, 620.0)
        db_guardar_flujo_caja("2026-06", 2200.0, 2450.0, 800.0, 780.0)
        db_guardar_flujo_caja("2026-07", 3500.0, 1200.0, 1200.0, 950.0)
        
        # Crear cuentas iniciales
        with get_connection() as conn:
            cursor = conn.cursor()
            
            fecha_vencida = (hoy - timedelta(days=4)).strftime("%Y-%m-%d")
            fecha_futura_1 = (hoy + timedelta(days=2)).strftime("%Y-%m-%d")
            fecha_futura_2 = (hoy + timedelta(days=5)).strftime("%Y-%m-%d")
            
            cursor.execute("""
                INSERT OR IGNORE INTO cuentas_cobrar (id, cliente, monto, vencimiento, estado)
                VALUES ('FAC-001', 'Banco del Norte (Alquiler Clon COBOL)', 850.0, ?, 'Pendiente')
            """, (fecha_vencida,))
            
            cursor.execute("""
                INSERT OR IGNORE INTO cuentas_cobrar (id, cliente, monto, vencimiento, estado)
                VALUES ('FAC-002', 'Consultora Tecno (Alquiler Clon Legal IA)', 1200.0, ?, 'Pendiente')
            """, (fecha_futura_2,))
            
            cursor.execute("""
                INSERT OR IGNORE INTO cuentas_cobrar (id, cliente, monto, vencimiento, estado)
                VALUES ('FAC-003', 'Startup Alpha (Asesoría Finanzas)', 400.0, ?, 'Cobrado')
            """, ((hoy - timedelta(days=10)).strftime("%Y-%m-%d"),))
            
            cursor.execute("""
                INSERT OR IGNORE INTO cuentas_pagar (id, proveedor, monto, vencimiento, estado)
                VALUES ('PROV-001', 'OpenAI / Gemini API (Infraestructura)', 350.0, ?, 'Pendiente')
            """, (fecha_futura_1,))
            
            cursor.execute("""
                INSERT OR IGNORE INTO cuentas_pagar (id, proveedor, monto, vencimiento, estado)
                VALUES ('PROV-002', 'Servidores Cloud AWS', 150.0, ?, 'Pendiente')
            """, ((hoy + timedelta(days=12)).strftime("%Y-%m-%d"),))
            
            cursor.execute("""
                INSERT OR IGNORE INTO cuentas_pagar (id, proveedor, monto, vencimiento, estado)
                VALUES ('PROV-003', 'Desarrollador Freelance (Soporte)', 500.0, ?, 'Pagado')
            """, ((hoy - timedelta(days=1)).strftime("%Y-%m-%d"),))
        return
    
    # Modo JSON legacy
    with db_lock:
        if not os.path.exists(DB_FINANZAS):
            hoy = datetime.now()
            fecha_futura_1 = (hoy + timedelta(days=2)).strftime("%Y-%m-%d")
            fecha_futura_2 = (hoy + timedelta(days=5)).strftime("%Y-%m-%d")
            fecha_vencida = (hoy - timedelta(days=4)).strftime("%Y-%m-%d")

            datos_iniciales = {
                "flujo_caja": {
                    "2026-05": {
                        "ingresos_plan": 1500.0,
                        "ingresos_real": 1420.0,
                        "egresos_plan": 600.0,
                        "egresos_real": 620.0
                    },
                    "2026-06": {
                        "ingresos_plan": 2200.0,
                        "ingresos_real": 2450.0,
                        "egresos_plan": 800.0,
                        "egresos_real": 780.0
                    },
                    "2026-07": {
                        "ingresos_plan": 3500.0,
                        "ingresos_real": 1200.0,
                        "egresos_plan": 1200.0,
                        "egresos_real": 950.0
                    }
                },
                "cuentas_cobrar": [
                    {
                        "id": "FAC-001",
                        "cliente": "Banco del Norte (Alquiler Clon COBOL)",
                        "monto": 850.0,
                        "vencimiento": fecha_vencida,
                        "estado": "Pendiente"
                    },
                    {
                        "id": "FAC-002",
                        "cliente": "Consultora Tecno (Alquiler Clon Legal IA)",
                        "monto": 1200.0,
                        "vencimiento": fecha_futura_2,
                        "estado": "Pendiente"
                    },
                    {
                        "id": "FAC-003",
                        "cliente": "Startup Alpha (Asesoría Finanzas)",
                        "monto": 400.0,
                        "vencimiento": (hoy - timedelta(days=10)).strftime("%Y-%m-%d"),
                        "estado": "Cobrado"
                    }
                ],
                "cuentas_pagar": [
                    {
                        "id": "PROV-001",
                        "proveedor": "OpenAI / Gemini API (Infraestructura)",
                        "monto": 350.0,
                        "vencimiento": fecha_futura_1,
                        "estado": "Pendiente"
                    },
                    {
                        "id": "PROV-002",
                        "proveedor": "Servidores Cloud AWS",
                        "monto": 150.0,
                        "vencimiento": (hoy + timedelta(days=12)).strftime("%Y-%m-%d"),
                        "estado": "Pendiente"
                    },
                    {
                        "id": "PROV-003",
                        "proveedor": "Desarrollador Freelance (Soporte)",
                        "monto": 500.0,
                        "vencimiento": (hoy - timedelta(days=1)).strftime("%Y-%m-%d"),
                        "estado": "Pagado"
                    }
                ]
            }
            with open(DB_FINANZAS, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)


def cargar_finanzas():
    """Carga todos los datos financieros."""
    if USE_SQLITE:
        flujo = db_cargar_flujo_caja()
        cuentas_cobrar = db_cargar_cuentas_cobrar()
        cuentas_pagar = db_cargar_cuentas_pagar()
        return {
            "flujo_caja": flujo,
            "cuentas_cobrar": cuentas_cobrar,
            "cuentas_pagar": cuentas_pagar
        }
    
    with db_lock:
        inicializar_finanzas()
        with open(DB_FINANZAS, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_finanzas(datos):
    """Guarda todos los datos financieros."""
    if USE_SQLITE:
        for mes, valores in datos.get("flujo_caja", {}).items():
            db_guardar_flujo_caja(
                mes,
                valores["ingresos_plan"],
                valores["ingresos_real"],
                valores["egresos_plan"],
                valores["egresos_real"]
            )
        return

    with db_lock:
        with open(DB_FINANZAS, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    from dep_operaciones.cli import menu
    menu()
