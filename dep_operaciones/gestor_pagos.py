"""
Sistema de Pagos para SkillTwin.
Maneja transacciones, facturación y estado de pago.
"""

import os
import json
from datetime import datetime
import uuid

DB_PAGOS = os.path.join(os.path.dirname(__file__), "pagos_db.json")


def inicializar_pagos():
    """Crea la base de datos de pagos si no existe."""
    if not os.path.exists(DB_PAGOS):
        datos_iniciales = {
            "transacciones": {},
            "facturas": {},
            "metodos_pago": ["tarjeta_credito", "transferencia_bancaria", "wallet_cripto"],
            "total_procesado": 0.0
        }
        with open(DB_PAGOS, "w", encoding="utf-8") as f:
            json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)


def cargar_pagos():
    """Carga la base de datos de pagos."""
    inicializar_pagos()
    with open(DB_PAGOS, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_pagos(datos):
    """Guarda la base de datos de pagos."""
    with open(DB_PAGOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def crear_factura(orden_id, cliente_email, monto_total, comision, 
                  cantidad_horas, tarifa_hora, descripcion_proyecto):
    """
    Crea una factura para la orden.
    Retorna el ID de factura.
    """
    
    datos = cargar_pagos()
    factura_id = f"FAC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    nueva_factura = {
        "id": factura_id,
        "orden_id": orden_id,
        "cliente_email": cliente_email,
        "fecha_emision": datetime.now().isoformat(),
        "fecha_vencimiento": (datetime.now() + __import__('datetime').timedelta(days=15)).isoformat(),
        "estado": "pendiente",  # pendiente, pagada, vencida, cancelada
        "monto_subtotal": monto_total - comision,
        "comision_plataforma": comision,
        "monto_total": monto_total,
        "moneda": "USD",
        "detalles": {
            "cantidad_horas": cantidad_horas,
            "tarifa_hora": tarifa_hora,
            "descripcion": descripcion_proyecto
        },
        "metodo_pago_seleccionado": None,
        "referencia_transaccion": None,
        "notas": f"Factura por servicios de consultoría. Proyecto: {descripcion_proyecto}"
    }
    
    datos["facturas"][factura_id] = nueva_factura
    guardar_pagos(datos)
    
    return factura_id, nueva_factura


def procesar_pago(factura_id, metodo_pago, numero_referencia=""):
    """
    Procesa un pago para una factura.
    Simula la transacción con un sistema de pagos ficticio.
    """
    
    datos = cargar_pagos()
    
    if factura_id not in datos["facturas"]:
        return False, "Factura no encontrada"
    
    factura = datos["facturas"][factura_id]
    
    if factura["estado"] == "pagada":
        return False, "La factura ya ha sido pagada"
    
    # Crear transacción
    transaccion_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:10].upper()}"
    
    transaccion = {
        "id": transaccion_id,
        "factura_id": factura_id,
        "orden_id": factura["orden_id"],
        "cliente_email": factura["cliente_email"],
        "monto": factura["monto_total"],
        "moneda": "USD",
        "metodo_pago": metodo_pago,
        "numero_referencia": numero_referencia or transaccion_id,
        "fecha_transaccion": datetime.now().isoformat(),
        "estado": "completada",  # completada, fallida, pendiente
        "codigo_autorizacion": f"AUTH-{uuid.uuid4().hex[:12].upper()}",
        "detalles_respuesta": {
            "banco": "Banco Simulado",
            "referencia_banco": uuid.uuid4().hex[:20].upper(),
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Actualizar factura
    factura["estado"] = "pagada"
    factura["metodo_pago_seleccionado"] = metodo_pago
    factura["referencia_transaccion"] = transaccion_id
    
    # Guardar transacción
    datos["transacciones"][transaccion_id] = transaccion
    datos["total_procesado"] = datos.get("total_procesado", 0) + factura["monto_total"]
    
    guardar_pagos(datos)
    
    return True, {
        "transaccion_id": transaccion_id,
        "factura_id": factura_id,
        "monto": factura["monto_total"],
        "estado": "completada",
        "codigo_autorizacion": transaccion["codigo_autorizacion"]
    }


def obtener_factura(factura_id):
    """Obtiene los detalles de una factura."""
    datos = cargar_pagos()
    return datos["facturas"].get(factura_id)


def listar_facturas(cliente_email=None):
    """Lista facturas, opcionalmente filtrando por cliente."""
    datos = cargar_pagos()
    facturas = list(datos["facturas"].values())
    
    if cliente_email:
        facturas = [f for f in facturas if f["cliente_email"] == cliente_email]
    
    return facturas


def obtener_transaccion(transaccion_id):
    """Obtiene detalles de una transacción."""
    datos = cargar_pagos()
    return datos["transacciones"].get(transaccion_id)


def listar_transacciones(cliente_email=None):
    """Lista transacciones, opcionalmente filtrando por cliente."""
    datos = cargar_pagos()
    transacciones = list(datos["transacciones"].values())
    
    if cliente_email:
        transacciones = [t for t in transacciones if t["cliente_email"] == cliente_email]
    
    return sorted(transacciones, key=lambda x: x["fecha_transaccion"], reverse=True)


def obtener_estadisticas_pagos():
    """Obtiene estadísticas de pagos del sistema."""
    datos = cargar_pagos()
    
    facturas = list(datos["facturas"].values())
    total_facturas = len(facturas)
    facturas_pagadas = len([f for f in facturas if f["estado"] == "pagada"])
    facturas_pendientes = len([f for f in facturas if f["estado"] == "pendiente"])
    
    transacciones = list(datos["transacciones"].values())
    total_transacciones = len(transacciones)
    
    return {
        "total_facturas": total_facturas,
        "facturas_pagadas": facturas_pagadas,
        "facturas_pendientes": facturas_pendientes,
        "total_transacciones": total_transacciones,
        "monto_total_procesado": datos.get("total_procesado", 0),
        "moneda": "USD"
    }
