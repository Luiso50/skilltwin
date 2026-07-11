import os
import json
import uuid
from datetime import datetime, timedelta

DB_ORDENES = os.path.join(os.path.dirname(__file__), "ordenes_db.json")

def inicializar_ordenes():
    """Crea la base de datos de órdenes si no existe."""
    if not os.path.exists(DB_ORDENES):
        datos_iniciales = {
            "ordenes": {},
            "contador_ordenes": 0
        }
        with open(DB_ORDENES, "w", encoding="utf-8") as f:
            json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)

def cargar_ordenes():
    inicializar_ordenes()
    with open(DB_ORDENES, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_ordenes(datos):
    with open(DB_ORDENES, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def crear_orden(cliente_email, clon_id, cantidad_horas, descripcion_proyecto, requiere_contrato=True):
    """
    Crea una nueva orden de servicio.
    Retorna el ID de la orden y comienza el procesamiento automático.
    """
    datos = cargar_ordenes()
    
    # Generar ID único
    orden_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    nueva_orden = {
        "id": orden_id,
        "cliente_email": cliente_email,
        "clon_id": clon_id,
        "cantidad_horas": cantidad_horas,
        "descripcion_proyecto": descripcion_proyecto,
        "requiere_contrato": requiere_contrato,
        "fecha_creacion": datetime.now().isoformat(),
        "estado": "pendiente",  # Estados: pendiente -> legal -> desarrollo -> operaciones -> completada -> entregada
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
                "mensaje": f"Orden creada exitosamente. Se procesará automáticamente.",
                "leida": False
            }
        ],
        "monto_total": None,
        "comision": None,
        "archivos_entregables": [],
        "pago": {
            "factura_id": None,
            "estado_pago": "pendiente",  # pendiente, pagada, fallida
            "metodo_pago": None,
            "fecha_pago": None
        },
        "rating": {
            "puntuacion": None,  # 1-5 estrellas
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
    
    datos["ordenes"][orden_id] = nueva_orden
    datos["contador_ordenes"] = datos.get("contador_ordenes", 0) + 1
    guardar_ordenes(datos)
    
    return orden_id, nueva_orden

def obtener_orden(orden_id):
    """Obtiene los detalles de una orden específica."""
    datos = cargar_ordenes()
    return datos["ordenes"].get(orden_id)

def listar_ordenes(cliente_email=None):
    """Lista todas las órdenes o filtra por cliente."""
    datos = cargar_ordenes()
    ordenes = list(datos["ordenes"].values())
    
    if cliente_email:
        ordenes = [o for o in ordenes if o["cliente_email"] == cliente_email]
    
    return ordenes

def actualizar_etapa_orden(orden_id, nombre_etapa, nuevo_estado, detalles=""):
    """Actualiza el estado de una etapa de la orden."""
    datos = cargar_ordenes()
    
    if orden_id not in datos["ordenes"]:
        return False, "Orden no encontrada"
    
    orden = datos["ordenes"][orden_id]
    
    if nombre_etapa not in orden["etapas"]:
        return False, f"Etapa '{nombre_etapa}' no existe"
    
    etapa = orden["etapas"][nombre_etapa]
    
    # Actualizar etapa
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
    
    # Actualizar detalles
    if detalles:
        etapa["detalles"] = detalles
    
    # Agregar notificación
    notificacion = {
        "timestamp": datetime.now().isoformat(),
        "tipo": "etapa_actualizada",
        "mensaje": f"Etapa '{nombre_etapa}' actualizada a '{nuevo_estado}'. {detalles}",
        "leida": False
    }
    orden["notificaciones"].append(notificacion)
    
    # Verificar si todas las etapas están completadas
    etapas_completadas = all(e["estado"] == "completada" for e in orden["etapas"].values())
    if etapas_completadas:
        orden["estado"] = "completada"
        notificacion_final = {
            "timestamp": datetime.now().isoformat(),
            "tipo": "completada",
            "mensaje": "¡Orden completada! Se está preparando para entrega.",
            "leida": False
        }
        orden["notificaciones"].append(notificacion_final)
    
    guardar_ordenes(datos)
    return True, "Etapa actualizada"

def marcar_notificacion_leida(orden_id, indice_notificacion):
    """Marca una notificación como leída."""
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
    
    # Agregar notificación
    notificacion = {
        "timestamp": datetime.now().isoformat(),
        "tipo": "rating_recibido",
        "mensaje": f"⭐ Calificación recibida: {puntuacion}/5 estrellas",
        "leida": False
    }
    orden["notificaciones"].append(notificacion)
    
    guardar_ordenes(datos)
    return True, "Calificación registrada"


def obtener_rating_experto(clon_id):
    """Obtiene la calificación promedio de un experto."""
    datos = cargar_ordenes()
    ordenes = datos["ordenes"].values()
    
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
    datos = cargar_ordenes()
    
    if orden_id not in datos["ordenes"]:
        return False
    
    orden = datos["ordenes"][orden_id]
    orden["pago"]["factura_id"] = factura_id
    orden["pago"]["metodo_pago"] = metodo_pago
    orden["pago"]["fecha_pago"] = datetime.now().isoformat()
    orden["pago"]["estado_pago"] = "pagada"
    
    notificacion = {
        "timestamp": datetime.now().isoformat(),
        "tipo": "pago_recibido",
        "mensaje": f"💰 Pago recibido exitosamente. Método: {metodo_pago}",
        "leida": False
    }
    orden["notificaciones"].append(notificacion)
    
    guardar_ordenes(datos)
    return True


def actualizar_contrato_orden(orden_id, texto_contrato, por_gemini=False):
    """Actualiza el contrato de una orden."""
    datos = cargar_ordenes()
    
    if orden_id not in datos["ordenes"]:
        return False
    
    orden = datos["ordenes"][orden_id]
    orden["contrato"]["texto_contrato"] = texto_contrato
    orden["contrato"]["generado_por_gemini"] = por_gemini
    orden["contrato"]["fecha_firma"] = datetime.now().isoformat()
    
    guardar_ordenes(datos)
    return True
