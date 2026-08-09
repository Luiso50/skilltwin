import json
import os
from datetime import datetime
import threading

def _use_sqlite():
    return os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"


DB_CONTACTOS = os.environ.get("SKILLTWIN_CONTACTOS_DB") or os.path.join(os.path.dirname(__file__), "contactos_db.json")
db_lock = threading.RLock()


def _get_sqlite_backend():
    from dep_operaciones.database import (
        cargar_contactos as db_cargar_contactos,
        guardar_contacto as db_guardar_contacto,
        init_database,
    )

    init_database()
    return db_cargar_contactos, db_guardar_contacto


def _build_contacto(nombre, email, telefono, empresa, interes, mensaje, contacto_id=None):
    if not contacto_id:
        contacto_id = f"CT-{datetime.now().strftime('%Y%m%d')}"
    return {
        "id": contacto_id,
        "nombre": nombre.strip(),
        "email": email.strip(),
        "telefono": (telefono or "").strip(),
        "empresa": (empresa or "").strip(),
        "interes": (interes or "").strip(),
        "mensaje": mensaje.strip(),
        "fecha": datetime.now().isoformat(),
        "estado": "nuevo"
    }


def inicializar_contactos():
    if _use_sqlite():
        return
    with db_lock:
        if not os.path.exists(DB_CONTACTOS):
            os.makedirs(os.path.dirname(DB_CONTACTOS), exist_ok=True)
            with open(DB_CONTACTOS, "w", encoding="utf-8") as f:
                json.dump({"contactos": []}, f, indent=4, ensure_ascii=False)


def cargar_contactos():
    if _use_sqlite():
        db_cargar_contactos, _db_guardar_contacto = _get_sqlite_backend()
        return {"contactos": db_cargar_contactos()}
    with db_lock:
        inicializar_contactos()
        with open(DB_CONTACTOS, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_contactos(datos):
    if _use_sqlite():
        return
    with db_lock:
        with open(DB_CONTACTOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


def registrar_contacto(nombre, email, telefono, empresa, interes, mensaje):
    if _use_sqlite():
        _db_cargar_contactos, db_guardar_contacto = _get_sqlite_backend()
        contacto_id = db_guardar_contacto(nombre.strip(), email.strip(), (telefono or "").strip(), (empresa or "").strip(), (interes or "").strip(), mensaje.strip())
        return _build_contacto(nombre, email, telefono, empresa, interes, mensaje, f"CT-{contacto_id}")

    datos = cargar_contactos()
    contacto = _build_contacto(nombre, email, telefono, empresa, interes, mensaje, f"CT-{datetime.now().strftime('%Y%m%d')}-{len(datos['contactos']) + 1:03d}")
    datos["contactos"].append(contacto)
    guardar_contactos(datos)
    return contacto
