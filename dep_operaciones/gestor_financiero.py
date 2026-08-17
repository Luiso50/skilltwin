import os
import json
from datetime import datetime, timedelta
import threading

def _use_sqlite():
    return os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"


USE_SQLITE = _use_sqlite()

DB_FINANZAS = os.path.join(os.path.dirname(__file__), "finanzas_db.json")
db_lock = threading.RLock()

if _use_sqlite():
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


def _build_seed_data():
    hoy = datetime.now()
    return {
        "flujo_caja": {
            "2026-05": {"ingresos_plan": 1500.0, "ingresos_real": 1420.0, "egresos_plan": 600.0, "egresos_real": 620.0},
            "2026-06": {"ingresos_plan": 2200.0, "ingresos_real": 2450.0, "egresos_plan": 800.0, "egresos_real": 780.0},
            "2026-07": {"ingresos_plan": 3500.0, "ingresos_real": 1200.0, "egresos_plan": 1200.0, "egresos_real": 950.0}
        },
        "cuentas_cobrar": [
            {"id": "FAC-001", "cliente": "Banco del Norte (Alquiler Clon COBOL)", "monto": 850.0, "vencimiento": (hoy - timedelta(days=4)).strftime("%Y-%m-%d"), "estado": "Pendiente"},
            {"id": "FAC-002", "cliente": "Consultora Tecno (Alquiler Clon Legal IA)", "monto": 1200.0, "vencimiento": (hoy + timedelta(days=5)).strftime("%Y-%m-%d"), "estado": "Pendiente"},
            {"id": "FAC-003", "cliente": "Startup Alpha (Asesoría Finanzas)", "monto": 400.0, "vencimiento": (hoy - timedelta(days=10)).strftime("%Y-%m-%d"), "estado": "Cobrado"}
        ],
        "cuentas_pagar": [
            {"id": "PROV-001", "proveedor": "OpenAI / Gemini API (Infraestructura)", "monto": 350.0, "vencimiento": (hoy + timedelta(days=2)).strftime("%Y-%m-%d"), "estado": "Pendiente"},
            {"id": "PROV-002", "proveedor": "Servidores Cloud AWS", "monto": 150.0, "vencimiento": (hoy + timedelta(days=12)).strftime("%Y-%m-%d"), "estado": "Pendiente"},
            {"id": "PROV-003", "proveedor": "Desarrollador Freelance (Soporte)", "monto": 500.0, "vencimiento": (hoy - timedelta(days=1)).strftime("%Y-%m-%d"), "estado": "Pagado"}
        ]
    }


def _seed_sqlite():
    flujo = db_cargar_flujo_caja()
    if flujo:
        return
    seed = _build_seed_data()
    for mes, v in seed["flujo_caja"].items():
        db_guardar_flujo_caja(mes, v["ingresos_plan"], v["ingresos_real"], v["egresos_plan"], v["egresos_real"])
    with get_connection() as conn:
        cursor = conn.cursor()
        for c in seed["cuentas_cobrar"]:
            cursor.execute("INSERT OR IGNORE INTO cuentas_cobrar (id, cliente, monto, vencimiento, estado) VALUES (?, ?, ?, ?, ?)", (c["id"], c["cliente"], c["monto"], c["vencimiento"], c["estado"]))
        for p in seed["cuentas_pagar"]:
            cursor.execute("INSERT OR IGNORE INTO cuentas_pagar (id, proveedor, monto, vencimiento, estado) VALUES (?, ?, ?, ?, ?)", (p["id"], p["proveedor"], p["monto"], p["vencimiento"], p["estado"]))


def inicializar_finanzas():
    if _use_sqlite():
        _seed_sqlite()
        return
    with db_lock:
        if not os.path.exists(DB_FINANZAS):
            os.makedirs(os.path.dirname(DB_FINANZAS), exist_ok=True)
            with open(DB_FINANZAS, "w", encoding="utf-8") as f:
                json.dump(_build_seed_data(), f, indent=4, ensure_ascii=False)


def cargar_finanzas():
    if _use_sqlite():
        return {"flujo_caja": db_cargar_flujo_caja(), "cuentas_cobrar": db_cargar_cuentas_cobrar(), "cuentas_pagar": db_cargar_cuentas_pagar()}
    with db_lock:
        inicializar_finanzas()
        with open(DB_FINANZAS, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_finanzas(datos):
    if _use_sqlite():
        for mes, valores in datos.get("flujo_caja", {}).items():
            db_guardar_flujo_caja(mes, valores["ingresos_plan"], valores["ingresos_real"],
                                  valores["egresos_plan"], valores["egresos_real"])
        with get_connection() as conn:
            cursor = conn.cursor()
            for c in datos.get("cuentas_cobrar", []):
                cursor.execute("""INSERT OR REPLACE INTO cuentas_cobrar (id, cliente, monto, vencimiento, estado)
                    VALUES (?, ?, ?, ?, ?)""", (c["id"], c["cliente"], c["monto"], c["vencimiento"], c["estado"]))
            for p in datos.get("cuentas_pagar", []):
                cursor.execute("""INSERT OR REPLACE INTO cuentas_pagar (id, proveedor, monto, vencimiento, estado)
                    VALUES (?, ?, ?, ?, ?)""", (p["id"], p["proveedor"], p["monto"], p["vencimiento"], p["estado"]))
        return
    with db_lock:
        with open(DB_FINANZAS, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    from dep_operaciones.cli import menu
    menu()
