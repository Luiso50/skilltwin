import json
import os
from datetime import datetime
import threading

DB_CONTACTOS = os.environ.get("SKILLTWIN_CONTACTOS_DB") or os.path.join(
    os.path.dirname(__file__), "contactos_db.json"
)
db_lock = threading.RLock()


def inicializar_contactos():
    with db_lock:
        if not os.path.exists(DB_CONTACTOS):
            datos_iniciales = {"contactos": []}
            with open(DB_CONTACTOS, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)


def cargar_contactos():
    with db_lock:
        inicializar_contactos()
        with open(DB_CONTACTOS, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_contactos(datos):
    with db_lock:
        with open(DB_CONTACTOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


def registrar_contacto(nombre, email, telefono, empresa, interes, mensaje):
    datos = cargar_contactos()
    contacto = {
        "id": f"CT-{datetime.now().strftime('%Y%m%d')}-{len(datos['contactos']) + 1:03d}",
        "nombre": nombre.strip(),
        "email": email.strip(),
        "telefono": telefono.strip(),
        "empresa": empresa.strip(),
        "interes": interes.strip(),
        "mensaje": mensaje.strip(),
        "fecha": datetime.now().isoformat(),
        "estado": "nuevo"
    }
    datos["contactos"].append(contacto)
    guardar_contactos(datos)
    return contacto
