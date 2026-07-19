import os
import json
import uuid
from datetime import datetime
import threading

# Soporte para JSON (legacy) y SQLite (nuevo)
USE_SQLITE = os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"

DB_ORDENES = os.path.join(os.path.dirname(__file__), "ordenes_db.json")
db_lock = threading.RLock()

if USE_SQLITE:
    try:
        from database import cargar_ordenes as db_cargar_ordenes
        from database import guardar_orden as db_guardar_orden
        from database import obtener_orden as db_obtener_orden
        from database import init_database
        init_database()
    except ImportError:
        USE_SQLITE = False


def _asegurar_esquema_orden(orden):
    actualizado = False

    if "archivos_entregables" not in orden:
        orden["archivos_entregables"] = []
        actualizado = True

    if "pago" not in orden:
        orden["pago"] = {
            "factura_id": None,
            "estado_pago": "pendiente",
            "metodo_pago": None,
            "fecha_pago": None
        }
        actualizado = True

    if "rating" not in orden:
        orden["rating"] = {
            "puntuacion": None,
            "resena": "",
            "fecha_rating": None,
            "cliente_satisfecho": None
        }
        actualizado = True

    if "contrato" not in orden:
        orden["contrato"] = {
            "texto_contrato": None,
            "generado_por_gemini": False,
            "firma_cliente": False,
            "fecha_firma": None
        }
        actualizado = True

    pago = orden.get("pago", {})
    if pago.get("metodo_pago") == "pendiente" and pago.get("estado_pago") == "pagada":
        pago["estado_pago"] = "pendiente"
        pago["metodo_pago"] = None
        pago["fecha_pago"] = None
        actualizado = True

    return actualizado


def inicializar_ordenes():
    """Crea la base de datos de órdenes si no existe."""
    if USE_SQLITE:
        return  # SQLite se inicializa automáticamente
    
    with db_lock:
        if not os.path.exists(DB_ORDENES):
            datos_iniciales = {
                "ordenes": {},
                "contador_ordenes": 0
            }
            with open(DB_ORDENES, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)


def cargar_ordenes():
    """Carga todas las órdenes."""
    if USE_SQLITE:
        ordenes_dict = db_cargar_ordenes()
        return {"ordenes": ordenes_dict, "contador_ordenes": len(ordenes_dict)}
    
    with db_lock:
        inicializar_ordenes()
        with open(DB_ORDENES, "r", encoding="utf-8") as f:
            datos = json.load(f)

        actualizado = False
        for orden in datos.get("ordenes", {}).values():
            actualizado = _asegurar_esquema_orden(orden) or actualizado

        if actualizado:
            guardar_ordenes(datos)

        return datos


def guardar_ordenes(datos):
    """Guarda todas las órdenes."""
    if USE_SQLITE:
        for orden_id, orden in datos.get("ordenes", {}).items():
            db_guardar_orden(orden)
        return
    
    with db_lock:
        with open(DB_ORDENES, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


def crear_orden(cliente_email, clon_id, cantidad_horas, descripcion_proyecto, requiere_contrato=True):
    """
    Crea una nueva orden de servicio.
    Retorna el ID de la orden y comienza el procesamiento automático.
    """
    orden_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    nueva_orden = {
        "id": orden_id,
        "cliente_email": cliente_email,
        "clon_id": clon_id,
        "cantidad_horas": cantidad_horas,
        "descripcion_proyecto": descripcion_proyecto,
        "requiere_contrato": requiere_contrato,
        "fecha_creacion": datetime.now().isoformat(),
        "estado": "pendiente",
        "etapas": {
            "legal": {
                "estado": "pendiente",
                "fecha_inicio": None,
                "fecha_fin": None,
                "detalles": "Esperando validación de contrato y política de privacidad"
            },
            "desarrollo": {
                "estado": "pendiente",
                "fecha_inicio": None,
                "fecha_fin": None,
                "detalles": "Esperando preparación del clon para el proyecto"
            },
            "operaciones": {
                "estado": "pendiente",
                "fecha_inicio": None,
                "fecha_fin": None,
                "detalles": "Esperando procesamiento financiero y facturación"
            },
            "entrega": {
                "estado": "pendiente",
                "fecha_inicio": None,
                "fecha_fin": None,
                "detalles": "Esperando envío de acceso al cliente"
            }
        },
        "notificaciones": [
            {
                "timestamp": datetime.now().isoformat(),
                "tipo": "creacion",
                "mensaje": "Orden creada exitosamente. Se procesará automáticamente.",
                "leida": False
            }
        ],
        "monto_total": None,
        "comision": None,
        "archivos_entregables": [],
        "pago": {
            "factura_id": None,
            "estado_pago": "pendiente",
            "metodo_pago": None,
            "fecha_pago": None
        },
        "rating": {
            "puntuacion": None,
            "resena": "",
            "fecha_rating": None,
            "cliente_satisfecho": None
        },
        "contrato": {
            "texto_contrato": None,
            "generado_por_gemini": False,
            "firma_cliente": False,
            "fecha_firma": None
        }
    }
    
    if USE_SQLITE:
        db_guardar_orden(nueva_orden)
    else:
        datos = cargar_ordenes()
        datos["ordenes"][orden_id] = nueva_orden
        datos["contador_ordenes"] = datos.get("contador_ordenes", 0) + 1
        guardar_ordenes(datos)
    
    return orden_id, nueva_orden


def obtener_orden(orden_id):
    """Obtiene los detalles de una orden específica."""
    if USE_SQLITE:
        return db_obtener_orden(orden_id)
    
    datos = cargar_ordenes()
    return datos["ordenes"].get(orden_id)


def listar_ordenes(cliente_email=None):
    """Lista todas las órdenes o filtra por cliente."""
    if USE_SQLITE:
        ordenes_dict = db_cargar_ordenes()
        ordenes = list(ordenes_dict.values())
    else:
        datos = cargar_ordenes()
        ordenes = list(datos["ordenes"].values())
    
    if cliente_email:
        ordenes = [o for o in ordenes if o["cliente_email"] == cliente_email]
    
    return ordenes


def actualizar_etapa_orden(orden_id, nombre_etapa, nuevo_estado, detalles=""):
    """Actualiza el estado de una etapa de la orden."""
    if USE_SQLITE:
        orden = db_obtener_orden(orden_id)
        if not orden:
            return False, "Orden no encontrada"
        
        if nombre_etapa not in orden["etapas"]:
            return False, f"Etapa '{nombre_etapa}' no existe"
        
        etapa = orden["etapas"][nombre_etapa]
        
        if nuevo_estado == "en_proceso":
            if etapa["estado"] == "pendiente":
                etapa["fecha_inicio"] = datetime.now().isoformat()
                etapa["estado"] = "en_proceso"
        elif nuevo_estado == "completada":
            etapa["fecha_fin"] = datetime.now().isoformat()
            etapa["estado"] = "completada"
        elif nuevo_estado == "error":
            etapa["estado"] = "error"
            etapa["fecha_fin"] = datetime.now().isoformat()
        
        if detalles:
            etapa["detalles"] = detalles
        
        notificacion = {
            "timestamp": datetime.now().isoformat(),
            "tipo": "etapa_actualizada",
            "mensaje": f"Etapa '{nombre_etapa}' actualizada a '{nuevo_estado}'. {detalles}",
            "leida": False
        }
        orden["notificaciones"].append(notificacion)
        
        etapas_completadas = all(e["estado"] == "completada" for e in orden["etapas"].values())
        if etapas_completadas:
            orden["estado"] = "completada"
            orden["notificaciones"].append({
                "timestamp": datetime.now().isoformat(),
                "tipo": "completada",
                "mensaje": "¡Orden completada! Se está preparando para entrega.",
                "leida": False
            })
        
        db_guardar_orden(orden)
        return True, "Etapa actualizada"
    
    datos = cargar_ordenes()
    
    if orden_id not in datos["ordenes"]:
        return False, "Orden no encontrada"
    
    orden = datos["ordenes"][orden_id]
    
    if nombre_etapa not in orden["etapas"]:
        return False, f"Etapa '{nombre_etapa}' no existe"
    
    etapa = orden["etapas"][nombre_etapa]
    
    if nuevo_estado == "en_proceso":
        if etapa["estado"] == "pendiente":
            etapa["fecha_inicio"] = datetime.now().isoformat()
            etapa["estado"] = "en_proceso"
    elif nuevo_estado == "completada":
        etapa["fecha_fin"] = datetime.now().isoformat()
        etapa["estado"] = "completada"
    elif nuevo_estado == "error":
        etapa["estado"] = "error"
        etapa["fecha_fin"] = datetime.now().isoformat()
    
    if detalles:
        etapa["detalles"] = detalles
    
    notificacion = {
        "timestamp": datetime.now().isoformat(),
        "tipo": "etapa_actualizada",
        "mensaje": f"Etapa '{nombre_etapa}' actualizada a '{nuevo_estado}'. {detalles}",
        "leida": False
    }
    orden["notificaciones"].append(notificacion)
    
    etapas_completadas = all(e["estado"] == "completada" for e in orden["etapas"].values())
    if etapas_completadas:
        orden["estado"] = "completada"
        orden["notificaciones"].append({
            "timestamp": datetime.now().isoformat(),
            "tipo": "completada",
            "mensaje": "¡Orden completada! Se está preparando para entrega.",
            "leida": False
        })
    
    guardar_ordenes(datos)
    return True, "Etapa actualizada"


def marcar_notificacion_leida(orden_id, indice_notificacion):
    """Marca una notificación como leída."""
    if USE_SQLITE:
        orden = db_obtener_orden(orden_id)
        if not orden:
            return False
        
        if 0 <= indice_notificacion < len(orden["notificaciones"]):
            orden["notificaciones"][indice_notificacion]["leida"] = True
            db_guardar_orden(orden)
            return True
        return False
    
    datos = cargar_ordenes()
    
    if orden_id in datos["ordenes"]:
        if 0 <= indice_notificacion < len(datos["ordenes"][orden_id]["notificaciones"]):
            datos["ordenes"][orden_id]["notificaciones"][indice_notificacion]["leida"] = True
            guardar_ordenes(datos)
            return True
    
    return False


def obtener_notificaciones_no_leidas(cliente_email):
    """Obtiene todas las notificaciones no leídas de un cliente."""
    ordenes = listar_ordenes(cliente_email)
    notificaciones = []
    
    for orden in ordenes:
        for i, notif in enumerate(orden["notificaciones"]):
            if not notif["leida"]:
                notif["orden_id"] = orden["id"]
                notif["indice"] = i
                notificaciones.append(notif)
    
    return sorted(notificaciones, key=lambda x: x["timestamp"], reverse=True)


def agregar_rating_orden(orden_id, puntuacion, resena=""):
    """
    Agrega una calificación a una orden completada.
    Puntuación: 1-5 estrellas
    """
    if USE_SQLITE:
        orden = db_obtener_orden(orden_id)
        if not orden:
            return False, "Orden no encontrada"
        
        if orden["estado"] != "completada":
            return False, "Solo se pueden calificar órdenes completadas"
        
        if orden["rating"]["puntuacion"] is not None:
            return False, "Esta orden ya ha sido calificada"
        
        if not (1 <= puntuacion <= 5):
            return False, "La puntuación debe estar entre 1 y 5"
        
        orden["rating"]["puntuacion"] = puntuacion
        orden["rating"]["resena"] = resena
        orden["rating"]["fecha_rating"] = datetime.now().isoformat()
        orden["rating"]["cliente_satisfecho"] = puntuacion >= 4
        
        orden["notificaciones"].append({
            "timestamp": datetime.now().isoformat(),
            "tipo": "rating_recibido",
            "mensaje": f"Calificación recibida: {puntuacion}/5 estrellas",
            "leida": False
        })
        
        db_guardar_orden(orden)
        return True, "Calificación registrada"
    
    datos = cargar_ordenes()
    
    if orden_id not in datos["ordenes"]:
        return False, "Orden no encontrada"
    
    orden = datos["ordenes"][orden_id]
    
    if orden["estado"] != "completada":
        return False, "Solo se pueden calificar órdenes completadas"
    
    if orden["rating"]["puntuacion"] is not None:
        return False, "Esta orden ya ha sido calificada"
    
    if not (1 <= puntuacion <= 5):
        return False, "La puntuación debe estar entre 1 y 5"
    
    orden["rating"]["puntuacion"] = puntuacion
    orden["rating"]["resena"] = resena
    orden["rating"]["fecha_rating"] = datetime.now().isoformat()
    orden["rating"]["cliente_satisfecho"] = puntuacion >= 4
    
    orden["notificaciones"].append({
        "timestamp": datetime.now().isoformat(),
        "tipo": "rating_recibido",
        "mensaje": f"Calificación recibida: {puntuacion}/5 estrellas",
        "leida": False
    })
    
    guardar_ordenes(datos)
    return True, "Calificación registrada"


def obtener_rating_experto(clon_id):
    """Obtiene la calificación promedio de un experto."""
    ordenes = listar_ordenes()
    
    ratings = [o["rating"]["puntuacion"] for o in ordenes 
               if o["clon_id"] == clon_id and o["rating"]["puntuacion"] is not None]
    
    if not ratings:
        return None
    
    promedio = sum(ratings) / len(ratings)
    return {
        "clon_id": clon_id,
        "puntuacion_promedio": round(promedio, 2),
        "total_calificaciones": len(ratings),
        "calificaciones": ratings
    }


def actualizar_pago_orden(orden_id, factura_id, metodo_pago):
    """Actualiza el estado de pago de una orden."""
    if USE_SQLITE:
        orden = db_obtener_orden(orden_id)
        if not orden:
            return False
        
        orden["pago"]["factura_id"] = factura_id
        if metodo_pago == "pendiente":
            orden["pago"]["metodo_pago"] = None
            orden["pago"]["fecha_pago"] = None
            orden["pago"]["estado_pago"] = "pendiente"
            orden["notificaciones"].append({
                "timestamp": datetime.now().isoformat(),
                "tipo": "factura_generada",
                "mensaje": f"Factura generada: {factura_id}. Pendiente de pago.",
                "leida": False
            })
        else:
            orden["pago"]["metodo_pago"] = metodo_pago
            orden["pago"]["fecha_pago"] = datetime.now().isoformat()
            orden["pago"]["estado_pago"] = "pagada"
            orden["notificaciones"].append({
                "timestamp": datetime.now().isoformat(),
                "tipo": "pago_recibido",
                "mensaje": f"Pago recibido exitosamente. Método: {metodo_pago}",
                "leida": False
            })
        
        db_guardar_orden(orden)
        return True
    
    datos = cargar_ordenes()
    
    if orden_id not in datos["ordenes"]:
        return False
    
    orden = datos["ordenes"][orden_id]
    orden["pago"]["factura_id"] = factura_id
    if metodo_pago == "pendiente":
        orden["pago"]["metodo_pago"] = None
        orden["pago"]["fecha_pago"] = None
        orden["pago"]["estado_pago"] = "pendiente"
        orden["notificaciones"].append({
            "timestamp": datetime.now().isoformat(),
            "tipo": "factura_generada",
            "mensaje": f"Factura generada: {factura_id}. Pendiente de pago.",
            "leida": False
        })
    else:
        orden["pago"]["metodo_pago"] = metodo_pago
        orden["pago"]["fecha_pago"] = datetime.now().isoformat()
        orden["pago"]["estado_pago"] = "pagada"
        orden["notificaciones"].append({
            "timestamp": datetime.now().isoformat(),
            "tipo": "pago_recibido",
            "mensaje": f"Pago recibido exitosamente. Método: {metodo_pago}",
            "leida": False
        })
    
    guardar_ordenes(datos)
    return True


def actualizar_contrato_orden(orden_id, texto_contrato, por_gemini=False):
    """Actualiza el contrato de una orden."""
    if USE_SQLITE:
        orden = db_obtener_orden(orden_id)
        if not orden:
            return False
        
        orden["contrato"]["texto_contrato"] = texto_contrato
        orden["contrato"]["generado_por_gemini"] = por_gemini
        orden["contrato"]["fecha_firma"] = datetime.now().isoformat()
        
        db_guardar_orden(orden)
        return True
    
    datos = cargar_ordenes()
    
    if orden_id not in datos["ordenes"]:
        return False
    
    orden = datos["ordenes"][orden_id]
    orden["contrato"]["texto_contrato"] = texto_contrato
    orden["contrato"]["generado_por_gemini"] = por_gemini
    orden["contrato"]["fecha_firma"] = datetime.now().isoformat()
    
    guardar_ordenes(datos)
    return True
