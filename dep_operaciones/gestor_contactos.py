import json
import os
from datetime import datetime
import threading

# Soporte para JSON (legacy) y SQLite (nuevo)
USE_SQLITE = os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"

DB_CONTACTOS = os.environ.get("SKILLTWIN_CONTACTOS_DB") or os.path.join(
    os.path.dirname(__file__), "contactos_db.json"
)
db_lock = threading.RLock()

if USE_SQLITE:
    try:
        from database import cargar_contactos as db_cargar_contactos
        from database import guardar_contacto as db_guardar_contacto
        from database import init_database
        init_database()
    except ImportError:
        USE_SQLITE = False


def inicializar_contactos():
    """Inicializa la base de datos de contactos."""
    if USE_SQLITE:
        return  # SQLite se inicializa automáticamente
    
    with db_lock:
        if not os.path.exists(DB_CONTACTOS):
            datos_iniciales = {"contactos": []}
            with open(DB_CONTACTOS, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)


def cargar_contactos():
    """Carga todos los contactos."""
    if USE_SQLITE:
        contactos = db_cargar_contactos()
        return {"contactos": contactos}
    
    with db_lock:
        inicializar_contactos()
        with open(DB_CONTACTOS, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_contactos(datos):
    """Guarda todos los contactos."""
    if USE_SQLITE:
        # En SQLite, los contactos se guardan individualmente
        return
    
    with db_lock:
        with open(DB_CONTACTOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


def registrar_contacto(nombre, email, telefono, empresa, interes, mensaje):
    """Registra un nuevo contacto."""
    if USE_SQLITE:
        contacto_id = db_guardar_contacto(
            nombre.strip(),
            email.strip(),
            telefono.strip() if telefono else "",
            empresa.strip() if empresa else "",
            interes.strip() if interes else "",
            mensaje.strip()
        )
        return {
            "id": f"CT-{contacto_id}",
            "nombre": nombre.strip(),
            "email": email.strip(),
            "telefono": telefono.strip() if telefono else "",
            "empresa": empresa.strip() if empresa else "",
            "interes": interes.strip() if interes else "",
            "mensaje": mensaje.strip(),
            "fecha": datetime.now().isoformat(),
            "estado": "nuevo"
        }
    
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
