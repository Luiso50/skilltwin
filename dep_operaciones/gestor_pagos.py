"""
Sistema de Pagos para SkillTwin.
Maneja transacciones, facturación y estado de pago.
"""

import os
import json
from datetime import datetime, timedelta
import uuid
import threading

# Soporte para JSON (legacy) y SQLite (nuevo)
USE_SQLITE = os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"

DB_PAGOS = os.path.join(os.path.dirname(__file__), "pagos_db.json")
db_lock = threading.RLock()

if USE_SQLITE:
    try:
        from database import cargar_facturas as db_cargar_facturas
        from database import guardar_factura as db_guardar_factura
        from database import obtener_factura as db_obtener_factura
        from database import get_connection
        from database import init_database
        init_database()
    except ImportError:
        USE_SQLITE = False


def inicializar_pagos():
    """Crea la base de datos de pagos si no existe."""
    if USE_SQLITE:
        return  # SQLite se inicializa automáticamente
    
    with db_lock:
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
    if USE_SQLITE:
        facturas_dict = db_cargar_facturas()
        
        # Cargar transacciones
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transacciones")
            transacciones = {row["id"]: dict(row) for row in cursor.fetchall()}
        
        total_procesado = sum(t["monto"] for t in transacciones.values() if t["estado"] == "completada")
        
        return {
            "facturas": facturas_dict,
            "transacciones": transacciones,
            "metodos_pago": ["tarjeta_credito", "transferencia_bancaria", "wallet_cripto"],
            "total_procesado": total_procesado
        }
    
    with db_lock:
        inicializar_pagos()
        with open(DB_PAGOS, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_pagos(datos):
    """Guarda la base de datos de pagos."""
    if USE_SQLITE:
        # Guardar facturas
        for fac_id, factura in datos.get("facturas", {}).items():
            db_guardar_factura(factura)
        
        # Guardar transacciones
        with get_connection() as conn:
            cursor = conn.cursor()
            for trans_id, trans in datos.get("transacciones", {}).items():
                cursor.execute("""
                    INSERT OR REPLACE INTO transacciones (id, factura_id, tipo, monto, metodo_pago, estado, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (trans["id"], trans.get("factura_id"), trans.get("tipo", "pago"),
                      trans["monto"], trans.get("metodo_pago"), trans["estado"],
                      trans.get("fecha_transaccion", datetime.now().isoformat())))
        return
    
    with db_lock:
        with open(DB_PAGOS, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


def crear_factura(orden_id, cliente_email, monto_total, comision, 
                  cantidad_horas, tarifa_hora, descripcion_proyecto):
    """
    Crea una factura para la orden.
    Retorna el ID de factura.
    """
    factura_id = f"FAC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    nueva_factura = {
        "id": factura_id,
        "orden_id": orden_id,
        "cliente_email": cliente_email,
        "fecha_emision": datetime.now().isoformat(),
        "fecha_vencimiento": (datetime.now() + timedelta(days=15)).isoformat(),
        "estado": "pendiente",
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
    
    if USE_SQLITE:
        db_guardar_factura(nueva_factura)
    else:
        datos = cargar_pagos()
        datos["facturas"][factura_id] = nueva_factura
        guardar_pagos(datos)
    
    return factura_id, nueva_factura


def reconciliar_facturas_con_ordenes():
    """Vincula o crea facturas faltantes para órdenes legacy con monto calculado."""
    from dep_operaciones import gestor_ordenes

    if USE_SQLITE:
        datos_pagos = cargar_pagos()
        datos_ordenes = gestor_ordenes.cargar_ordenes()
        cambios = 0

        for orden_id, orden in datos_ordenes.get("ordenes", {}).items():
            if orden.get("monto_total") is None or orden.get("comision") is None:
                continue

            pago = orden.setdefault("pago", {
                "factura_id": None,
                "estado_pago": "pendiente",
                "metodo_pago": None,
                "fecha_pago": None
            })

            factura_id = pago.get("factura_id")
            if factura_id and factura_id in datos_pagos["facturas"]:
                continue

            factura_existente = next(
                (factura for factura in datos_pagos["facturas"].values() if factura.get("orden_id") == orden_id),
                None
            )

            if factura_existente:
                pago["factura_id"] = factura_existente["id"]
                pago["estado_pago"] = "pagada" if factura_existente.get("estado") == "pagada" else "pendiente"
                if pago["estado_pago"] != "pagada":
                    pago["metodo_pago"] = None
                    pago["fecha_pago"] = None
                cambios += 1
                continue

            subtotal = orden["monto_total"] - orden["comision"]
            cantidad_horas = orden.get("cantidad_horas") or 0
            tarifa_hora = round(subtotal / cantidad_horas, 2) if cantidad_horas else 0
            nueva_factura_id = f"FAC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            fecha_emision = orden.get("fecha_creacion") or datetime.now().isoformat()

            nueva_factura = {
                "id": nueva_factura_id,
                "orden_id": orden_id,
                "cliente_email": orden.get("cliente_email", ""),
                "fecha_emision": fecha_emision,
                "fecha_vencimiento": (datetime.fromisoformat(fecha_emision) + timedelta(days=15)).isoformat(),
                "estado": "pendiente",
                "monto_subtotal": subtotal,
                "comision_plataforma": orden["comision"],
                "monto_total": orden["monto_total"],
                "moneda": "USD",
                "detalles": {
                    "cantidad_horas": cantidad_horas,
                    "tarifa_hora": tarifa_hora,
                    "descripcion": orden.get("descripcion_proyecto", "")
                },
                "metodo_pago_seleccionado": None,
                "referencia_transaccion": None,
                "notas": f"Factura reconciliada automáticamente para la orden {orden_id}."
            }
            datos_pagos["facturas"][nueva_factura_id] = nueva_factura

            pago["factura_id"] = nueva_factura_id
            pago["estado_pago"] = "pendiente"
            pago["metodo_pago"] = None
            pago["fecha_pago"] = None
            cambios += 1

        if cambios:
            guardar_pagos(datos_pagos)
            gestor_ordenes.guardar_ordenes(datos_ordenes)

        return cambios
    
    datos_pagos = cargar_pagos()
    datos_ordenes = gestor_ordenes.cargar_ordenes()
    cambios = 0

    for orden_id, orden in datos_ordenes.get("ordenes", {}).items():
        if orden.get("monto_total") is None or orden.get("comision") is None:
            continue

        pago = orden.setdefault("pago", {
            "factura_id": None,
            "estado_pago": "pendiente",
            "metodo_pago": None,
            "fecha_pago": None
        })

        factura_id = pago.get("factura_id")
        if factura_id and factura_id in datos_pagos["facturas"]:
            continue

        factura_existente = next(
            (factura for factura in datos_pagos["facturas"].values() if factura.get("orden_id") == orden_id),
            None
        )

        if factura_existente:
            pago["factura_id"] = factura_existente["id"]
            pago["estado_pago"] = "pagada" if factura_existente.get("estado") == "pagada" else "pendiente"
            if pago["estado_pago"] != "pagada":
                pago["metodo_pago"] = None
                pago["fecha_pago"] = None
            cambios += 1
            continue

        subtotal = orden["monto_total"] - orden["comision"]
        cantidad_horas = orden.get("cantidad_horas") or 0
        tarifa_hora = round(subtotal / cantidad_horas, 2) if cantidad_horas else 0
        nueva_factura_id = f"FAC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        fecha_emision = orden.get("fecha_creacion") or datetime.now().isoformat()

        datos_pagos["facturas"][nueva_factura_id] = {
            "id": nueva_factura_id,
            "orden_id": orden_id,
            "cliente_email": orden.get("cliente_email"),
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": (datetime.fromisoformat(fecha_emision) + timedelta(days=15)).isoformat(),
            "estado": "pendiente",
            "monto_subtotal": subtotal,
            "comision_plataforma": orden["comision"],
            "monto_total": orden["monto_total"],
            "moneda": "USD",
            "detalles": {
                "cantidad_horas": cantidad_horas,
                "tarifa_hora": tarifa_hora,
                "descripcion": orden.get("descripcion_proyecto", "")
            },
            "metodo_pago_seleccionado": None,
            "referencia_transaccion": None,
            "notas": f"Factura reconciliada automáticamente para la orden {orden_id}."
        }

        pago["factura_id"] = nueva_factura_id
        pago["estado_pago"] = "pendiente"
        pago["metodo_pago"] = None
        pago["fecha_pago"] = None
        cambios += 1

    if cambios:
        guardar_pagos(datos_pagos)
        gestor_ordenes.guardar_ordenes(datos_ordenes)

    return cambios


def procesar_pago(factura_id, metodo_pago, numero_referencia=""):
    """
    Procesa un pago para una factura.
    Simula la transacción con un sistema de pagos ficticio.
    """
    if USE_SQLITE:
        factura = db_obtener_factura(factura_id)
        if not factura:
            return False, "Factura no encontrada"
        
        if factura["estado"] == "pagada":
            return False, "La factura ya ha sido pagada"
        
        transaccion_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:10].upper()}"
        
        transaccion = {
            "id": transaccion_id,
            "factura_id": factura_id,
            "orden_id": factura.get("orden_id"),
            "cliente_email": factura.get("cliente_email", ""),
            "monto": factura["monto_total"],
            "moneda": "USD",
            "metodo_pago": metodo_pago,
            "numero_referencia": numero_referencia or transaccion_id,
            "fecha_transaccion": datetime.now().isoformat(),
            "estado": "completada",
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
        db_guardar_factura(factura)
        
        # Guardar transacción
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transacciones (id, factura_id, tipo, monto, metodo_pago, estado, fecha)
                VALUES (?, ?, 'pago', ?, ?, 'completada', ?)
            """, (transaccion_id, factura_id, factura["monto_total"], metodo_pago,
                  datetime.now().isoformat()))
        
        return True, {
            "transaccion_id": transaccion_id,
            "factura_id": factura_id,
            "monto": factura["monto_total"],
            "estado": "completada",
            "codigo_autorizacion": transaccion["codigo_autorizacion"]
        }
    
    datos = cargar_pagos()
    
    if factura_id not in datos["facturas"]:
        return False, "Factura no encontrada"
    
    factura = datos["facturas"][factura_id]
    
    if factura["estado"] == "pagada":
        return False, "La factura ya ha sido pagada"
    
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
        "estado": "completada",
        "codigo_autorizacion": f"AUTH-{uuid.uuid4().hex[:12].upper()}",
        "detalles_respuesta": {
            "banco": "Banco Simulado",
            "referencia_banco": uuid.uuid4().hex[:20].upper(),
            "timestamp": datetime.now().isoformat()
        }
    }
    
    factura["estado"] = "pagada"
    factura["metodo_pago_seleccionado"] = metodo_pago
    factura["referencia_transaccion"] = transaccion_id
    
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
    if USE_SQLITE:
        return db_obtener_factura(factura_id)
    
    datos = cargar_pagos()
    return datos["facturas"].get(factura_id)


def listar_facturas(cliente_email=None):
    """Lista facturas, opcionalmente filtrando por cliente."""
    if USE_SQLITE:
        facturas_dict = db_cargar_facturas()
        facturas = list(facturas_dict.values())
    else:
        datos = cargar_pagos()
        facturas = list(datos["facturas"].values())
    
    if cliente_email:
        facturas = [f for f in facturas if f["cliente_email"] == cliente_email]
    
    return facturas


def obtener_transaccion(transaccion_id):
    """Obtiene detalles de una transacción."""
    if USE_SQLITE:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transacciones WHERE id = ?", (transaccion_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    datos = cargar_pagos()
    return datos["transacciones"].get(transaccion_id)


def listar_transacciones(cliente_email=None):
    """Lista transacciones, opcionalmente filtrando por cliente."""
    if USE_SQLITE:
        with get_connection() as conn:
            cursor = conn.cursor()
            if cliente_email:
                cursor.execute("""
                    SELECT t.* FROM transacciones t
                    JOIN facturas f ON t.factura_id = f.id
                    WHERE f.cliente_email = ?
                    ORDER BY t.fecha DESC
                """, (cliente_email,))
            else:
                cursor.execute("SELECT * FROM transacciones ORDER BY fecha DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    datos = cargar_pagos()
    transacciones = list(datos["transacciones"].values())
    
    if cliente_email:
        transacciones = [t for t in transacciones if t["cliente_email"] == cliente_email]
    
    return sorted(transacciones, key=lambda x: x["fecha_transaccion"], reverse=True)


def obtener_estadisticas_pagos():
    """Obtiene estadísticas de pagos del sistema."""
    if USE_SQLITE:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM facturas")
            total_facturas = cursor.fetchone()["total"]
            
            cursor.execute("SELECT COUNT(*) as pagadas FROM facturas WHERE estado = 'pagada'")
            facturas_pagadas = cursor.fetchone()["pagadas"]
            
            cursor.execute("SELECT COUNT(*) as pendientes FROM facturas WHERE estado = 'pendiente'")
            facturas_pendientes = cursor.fetchone()["pendientes"]
            
            cursor.execute("SELECT COUNT(*) as total FROM transacciones")
            total_transacciones = cursor.fetchone()["total"]
            
            cursor.execute("SELECT COALESCE(SUM(monto), 0) as total FROM transacciones WHERE estado = 'completada'")
            monto_total = cursor.fetchone()["total"]
        
        return {
            "total_facturas": total_facturas,
            "facturas_pagadas": facturas_pagadas,
            "facturas_pendientes": facturas_pendientes,
            "total_transacciones": total_transacciones,
            "monto_total_procesado": monto_total,
            "moneda": "USD"
        }
    
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
