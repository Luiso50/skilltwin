import logging
import urllib.parse
from dep_operaciones import gestor_ordenes, gestor_pagos, security

logger = logging.getLogger('cerebro')


def handle_ordenes(handler):
    try:
        auth_data = handler.require_customer_or_admin()
        if not auth_data:
            return

        if auth_data.get("role") == "admin":
            parsed = urllib.parse.urlparse(handler.path)
            params = urllib.parse.parse_qs(parsed.query)
            cliente_email = params.get("email", [None])[0]
        else:
            cliente_email = auth_data.get("email")

        ordenes = gestor_ordenes.listar_ordenes(cliente_email)
        handler.send_json_response({"ordenes": ordenes})
    except Exception as e:
        logger.error(f"Error listando ordenes: {e}")
        handler.send_error_response("Error interno del servidor", status=500)


def handle_facturas(handler):
    try:
        auth_data = handler.require_customer_or_admin()
        if not auth_data:
            return

        parsed = urllib.parse.urlparse(handler.path)
        params = urllib.parse.parse_qs(parsed.query)
        cliente_email = params.get("email", [None])[0]

        if auth_data.get("role") != "admin":
            cliente_email = auth_data.get("email")

        facturas = gestor_pagos.listar_facturas(cliente_email)
        handler.send_json_response({"facturas": facturas})
    except Exception as e:
        logger.error(f"Error listando facturas: {e}")
        handler.send_error_response("Error interno del servidor", status=500)


def handle_notificaciones(handler):
    try:
        auth_data = handler.require_customer_or_admin()
        if not auth_data:
            return

        if auth_data.get("role") == "admin":
            parsed = urllib.parse.urlparse(handler.path)
            params = urllib.parse.parse_qs(parsed.query)
            cliente_email = params.get("email", [None])[0]
        else:
            cliente_email = auth_data.get("email")

        if not cliente_email:
            handler.send_error_response("Email de cliente requerido", status=400)
            return

        notificaciones = gestor_ordenes.obtener_notificaciones_no_leidas(cliente_email)
        handler.send_json_response({"notificaciones": notificaciones})
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones: {e}")
        handler.send_error_response("Error al obtener notificaciones", status=400)


def handle_crear_orden(handler):
    try:
        auth_data = handler.require_customer_or_admin()
        if not auth_data:
            return
        if not handler.require_csrf():
            return

        data = handler.read_json_body()
        cliente_email = security.sanitize_string(data.get("cliente_email", ""), 254)
        if auth_data.get("role") == "customer":
            cliente_email = auth_data.get("email", "")
        clon_id = security.sanitize_string(data.get("clon_id", ""), 50)
        cantidad_horas = data.get("cantidad_horas", 0)
        descripcion_proyecto = security.sanitize_string(data.get("descripcion_proyecto", ""), 500)
        requiere_contrato = data.get("requiere_contrato", True)

        if not cliente_email or not clon_id or cantidad_horas <= 0:
            raise ValueError("Datos incompletos o inválidos")

        if not security.validate_email(cliente_email):
            raise ValueError("Formato de email inválido")

        if not security.validate_clon_id(clon_id):
            raise ValueError("ID de clon inválido")

        orden_id, orden_data = gestor_ordenes.crear_orden(
            cliente_email, clon_id, cantidad_horas,
            descripcion_proyecto, requiere_contrato
        )

        handler.send_json_response({
            "success": True,
            "orden_id": orden_id,
            "mensaje": "Orden creada exitosamente. Se procesará automáticamente.",
            "orden": orden_data
        }, status=201)
    except Exception as e:
        logger.error(f"Error en /api/crear-orden: {e}")
        handler.send_error_response(str(e), 400)


def handle_marcar_leida(handler):
    try:
        auth_data = handler.require_customer_or_admin()
        if not auth_data:
            return
        if not handler.require_csrf():
            return

        data = handler.read_json_body()
        orden_id = data.get("orden_id", "").strip()
        indice = data.get("indice", 0)
        orden = gestor_ordenes.obtener_orden(orden_id)
        if not orden:
            handler.send_error_response("Orden no encontrada o no autorizada", 404)
            return
        if not handler.require_resource_owner(orden.get("cliente_email"), auth_data):
            return

        exito = gestor_ordenes.marcar_notificacion_leida(orden_id, indice)

        handler.send_json_response({
            "success": exito,
            "mensaje": "Notificación marcada como leída"
        })
    except Exception as e:
        logger.error(f"Error en /api/marcar-leida: {e}")
        handler.send_error_response(str(e), 400)


def handle_agregar_rating(handler):
    try:
        auth_data = handler.require_customer_or_admin()
        if not auth_data:
            return
        if not handler.require_csrf():
            return

        data = handler.read_json_body()
        orden_id = security.sanitize_string(data.get("orden_id", ""), 50)
        puntuacion = data.get("puntuacion", 0)
        resena = security.sanitize_string(data.get("resena", ""), 500)
        orden = gestor_ordenes.obtener_orden(orden_id)
        if not orden:
            handler.send_error_response("Orden no encontrada o no autorizada", 404)
            return
        if not handler.require_resource_owner(orden.get("cliente_email"), auth_data):
            return

        if not security.validate_puntuacion(puntuacion):
            raise ValueError("Puntuación inválida (debe ser 1-5)")

        exito, mensaje = gestor_ordenes.agregar_rating_orden(orden_id, puntuacion, resena)

        if exito:
            handler.send_json_response({"success": True, "mensaje": mensaje})
        else:
            handler.send_error_response(mensaje)
    except Exception as e:
        logger.error(f"Error en /api/agregar-rating: {e}")
        handler.send_error_response(str(e), 500)


def handle_procesar_pago(handler):
    try:
        auth_data = handler.require_customer_or_admin()
        if not auth_data:
            return
        if not handler.require_csrf():
            return

        data = handler.read_json_body()
        factura_id = data.get("factura_id", "")
        metodo_pago = data.get("metodo_pago", "tarjeta_credito")
        if not isinstance(factura_id, str) or not isinstance(metodo_pago, str):
            raise ValueError("Datos de pago inválidos")
        factura_id = factura_id.strip()
        metodo_pago = metodo_pago.strip()
        factura = gestor_pagos.obtener_factura(factura_id)
        if not factura:
            handler.send_error_response("Factura no encontrada", 404)
            return
        if not handler.require_resource_owner(factura.get("cliente_email"), auth_data):
            return

        exito, resultado = gestor_pagos.procesar_pago(factura_id, metodo_pago)

        if exito:
            factura = gestor_pagos.obtener_factura(factura_id)
            if factura:
                gestor_ordenes.actualizar_pago_orden(
                    factura["orden_id"], factura_id, metodo_pago
                )

            handler.send_json_response({
                "success": True,
                "mensaje": "Pago procesado exitosamente",
                "resultado": resultado
            })
        else:
            handler.send_error_response(resultado)
    except ValueError as e:
        logger.warning(f"Solicitud inválida en /api/procesar-pago: {e}")
        handler.send_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error en /api/procesar-pago: {e}")
        handler.send_error_response(str(e), 500)
