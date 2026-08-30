import os
import logging
from dep_operaciones import stripe_service, gestor_pagos, gestor_ordenes, security

logger = logging.getLogger('cerebro')


def get_pending_invoice(factura_id):
    factura = gestor_pagos.obtener_factura(factura_id)
    if not factura:
        raise ValueError("Factura no encontrada")
    if factura.get("estado") != "pendiente":
        raise ValueError("La factura no está pendiente de pago")
    amount_cents = round(float(factura["monto_total"]) * 100)
    if amount_cents <= 0:
        raise ValueError("La factura no tiene un monto válido")
    return factura, amount_cents


def register_stripe_payment(factura_id, orden_id, amount_cents, reference):
    factura = gestor_pagos.obtener_factura(factura_id)
    if not factura:
        raise ValueError("Factura no encontrada")
    if factura.get("orden_id") != orden_id:
        raise ValueError("La orden no coincide con la factura")
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise ValueError("Stripe no proporcionó un importe válido")
    if round(float(factura["monto_total"]) * 100) != amount_cents:
        raise ValueError("El importe de Stripe no coincide con la factura")
    if factura.get("estado") == "pagada":
        return
    if factura.get("estado") != "pendiente":
        raise ValueError("La factura no está pendiente de pago")
    success, result = gestor_pagos.procesar_pago(factura_id, "stripe", reference)
    if not success:
        raise ValueError(result)
    gestor_ordenes.actualizar_pago_orden(orden_id, factura_id, "stripe")


def handle_stripe_config(handler):
    try:
        publishable_key = stripe_service.get_publishable_key()
        configured = stripe_service.is_stripe_configured()
        handler.send_json_response({
            "configured": configured,
            "publishable_key": publishable_key
        })
    except Exception as e:
        logger.error(f"Error al obtener configuración de Stripe: {e}")
        handler.send_error_response("Error interno del servidor", 500)


def handle_stripe_create_payment(handler):
    if not handler.require_admin():
        return
    try:
        data = handler.read_json_body()
        factura_id = security.sanitize_string(data.get("factura_id", ""), 50)
        factura, amount_cents = get_pending_invoice(factura_id)
        metadata = {
            "factura_id": factura_id,
            "orden_id": factura["orden_id"],
        }

        client_secret, error = stripe_service.create_payment_intent(
            amount_cents=amount_cents,
            metadata=metadata
        )

        if error:
            handler.send_error_response(error)
        else:
            handler.send_json_response({
                "success": True,
                "client_secret": client_secret
            })
    except ValueError as e:
        logger.warning(f"Solicitud Stripe inválida en /api/stripe/create-payment: {e}")
        handler.send_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error en /api/stripe/create-payment: {e}")
        handler.send_error_response(str(e), 500)


def handle_stripe_create_checkout(handler):
    if not handler.require_admin():
        return
    try:
        data = handler.read_json_body()
        factura_id = security.sanitize_string(data.get("factura_id", ""), 50)
        factura, amount_cents = get_pending_invoice(factura_id)
        public_url = os.environ.get("SKILLTWIN_PUBLIC_URL", "").rstrip("/")
        if not public_url:
            raise ValueError("SKILLTWIN_PUBLIC_URL debe configurarse para crear pagos")

        session_url, error = stripe_service.create_checkout_session(
            amount_cents=amount_cents,
            factura_id=factura_id,
            orden_id=factura["orden_id"],
            success_url=f"{public_url}/gracias.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{public_url}/client-portal.html"
        )

        if error:
            handler.send_error_response(error)
        else:
            handler.send_json_response({
                "success": True,
                "url": session_url
            })
    except ValueError as e:
        logger.warning(f"Solicitud Stripe inválida en /api/stripe/create-checkout: {e}")
        handler.send_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error en /api/stripe/create-checkout: {e}")
        handler.send_error_response(str(e), 500)


def handle_stripe_confirm_session(handler):
    auth_data = handler.require_customer_or_admin()
    if not auth_data:
        return
    try:
        data = handler.read_json_body()
        session_id = data.get("session_id", "").strip()

        if not session_id:
            handler.send_error_response("session_id es requerido")
            return

        session_data, error = stripe_service.retrieve_checkout_session(session_id)

        if error:
            handler.send_error_response(error)
            return

        if session_data["payment_status"] == "paid":
            factura_id = session_data["metadata"].get("factura_id")
            orden_id = session_data["metadata"].get("orden_id")

            if not factura_id or not orden_id:
                raise ValueError("La sesión de Stripe no contiene la factura y orden requeridas")
            factura = gestor_pagos.obtener_factura(factura_id)
            if not factura:
                handler.send_error_response("Factura no encontrada", 404)
                return
            if not handler.require_resource_owner(factura.get("cliente_email"), auth_data):
                return
            register_stripe_payment(
                factura_id,
                orden_id,
                session_data["amount_total"],
                session_data["id"],
            )

            handler.send_json_response({
                "success": True,
                "paid": True,
            })
        else:
            handler.send_json_response({
                "success": True,
                "paid": False,
            })
    except ValueError as e:
        logger.warning(f"Solicitud Stripe inválida en /api/stripe/confirm-session: {e}")
        handler.send_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error en /api/stripe/confirm-session: {e}")
        handler.send_error_response(str(e), 500)


def handle_stripe_webhook(handler):
    try:
        content_length = int(handler.headers.get("Content-Length", 0))
        payload = handler.rfile.read(content_length)
        sig_header = handler.headers.get("Stripe-Signature", "")
        event, error = stripe_service.handle_webhook(payload, sig_header)
        if error:
            handler.send_error_response(error, 400)
            return
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            metadata = session.get("metadata", {})
            factura_id = metadata.get("factura_id")
            orden_id = metadata.get("orden_id")
            amount_total = session.get("amount_total")
            if factura_id and orden_id:
                register_stripe_payment(factura_id, orden_id, amount_total, session["id"])
        elif event["type"] == "payment_intent.succeeded":
            pi = event["data"]["object"]
            metadata = pi.get("metadata", {})
            factura_id = metadata.get("factura_id")
            orden_id = metadata.get("orden_id")
            amount = pi.get("amount")
            if factura_id and orden_id:
                register_stripe_payment(factura_id, orden_id, amount, pi["id"])
        handler.send_json_response({"received": True})
    except ValueError as e:
        logger.warning(f"Solicitud Stripe inválida en /api/stripe/webhook: {e}")
        handler.send_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Error procesando webhook de Stripe: {e}")
        handler.send_error_response("Error procesando webhook", 500)
