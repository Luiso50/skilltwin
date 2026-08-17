import os


def get_stripe_config():
    """Obtiene la configuración de Stripe desde variables de entorno."""
    return {
        "secret_key": os.environ.get("STRIPE_SECRET_KEY", ""),
        "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
        "webhook_secret": os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    }


def is_stripe_configured():
    """Verifica si Stripe está configurado."""
    config = get_stripe_config()
    return bool(config["secret_key"])


def create_payment_intent(amount_cents, currency="usd", metadata=None):
    """
    Crea un PaymentIntent en Stripe.
    Retorna (client_secret, error_message)
    """
    config = get_stripe_config()

    if not config["secret_key"]:
        return None, "Stripe no configurado. Configura STRIPE_SECRET_KEY en variables de entorno."

    try:
        import stripe
        stripe.api_key = config["secret_key"]

        intent_data = {
            "amount": amount_cents,
            "currency": currency,
            "payment_method_types": ["card"],
        }

        if metadata:
            intent_data["metadata"] = metadata

        intent = stripe.PaymentIntent.create(**intent_data)

        return intent.client_secret, None

    except ImportError:
        return None, "Stripe SDK no instalado. Ejecuta: pip install stripe"
    except Exception as e:
        return None, f"Error creando PaymentIntent: {str(e)}"


def confirm_payment(payment_intent_id):
    """
    Confirma un pago existente.
    Retorna (exito, datos_o_error)
    """
    config = get_stripe_config()

    if not config["secret_key"]:
        return False, "Stripe no configurado"

    try:
        import stripe
        stripe.api_key = config["secret_key"]

        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if intent.status == "succeeded":
            return True, {
                "payment_intent_id": intent.id,
                "amount": intent.amount,
                "currency": intent.currency,
                "status": intent.status
            }
        else:
            return False, f"Pago en estado: {intent.status}"

    except Exception as e:
        return False, f"Error confirmando pago: {str(e)}"


def handle_webhook(payload, sig_header):
    """
    Maneja webhooks de Stripe.
    Retorna (evento, error_message)
    """
    config = get_stripe_config()

    if not config["webhook_secret"]:
        return None, "Webhook secret no configurado"

    try:
        import stripe
        stripe.api_key = config["secret_key"]

        event = stripe.Webhook.construct_event(
            payload, sig_header, config["webhook_secret"]
        )

        return event, None

    except ImportError:
        return None, "Stripe SDK no instalado"
    except Exception as e:
        return None, f"Error verificando webhook: {str(e)}"


def create_checkout_session(amount_cents, factura_id, orden_id=None, success_url=None, cancel_url=None):
    """
    Crea una sesión de Checkout de Stripe.
    Retorna (session_url, error_message)
    """
    config = get_stripe_config()

    if not config["secret_key"]:
        return None, "Stripe no configurado. Configura STRIPE_SECRET_KEY en variables de entorno."

    try:
        import stripe
        stripe.api_key = config["secret_key"]

        base_url = os.environ.get("SKILLTWIN_PUBLIC_URL", "http://localhost:8000")
        if not success_url:
            success_url = f"{base_url}/gracias.html?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{base_url}/client-portal.html"

        session_data = {
            "payment_method_types": ["card"],
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "SkillTwin - Servicio de Consultoría",
                        "description": f"Factura: {factura_id}"
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }],
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "factura_id": factura_id,
                "orden_id": orden_id or ""
            }
        }

        session = stripe.checkout.Session.create(**session_data)

        return session.url, None

    except ImportError:
        return None, "Stripe SDK no instalado. Ejecuta: pip install stripe"
    except Exception as e:
        return None, f"Error creando sesión de Checkout: {str(e)}"


def retrieve_checkout_session(session_id):
    """
    Obtiene los datos de una sesión de Checkout.
    Retorna (session_data, error_message)
    """
    config = get_stripe_config()

    if not config["secret_key"]:
        return None, "Stripe no configurado"

    try:
        import stripe
        stripe.api_key = config["secret_key"]

        session = stripe.checkout.Session.retrieve(session_id)

        return {
            "id": session.id,
            "payment_status": session.payment_status,
            "amount_total": session.amount_total,
            "currency": session.currency,
            "metadata": session.metadata
        }, None

    except ImportError:
        return None, "Stripe SDK no instalado"
    except Exception as e:
        return None, f"Error obteniendo sesión: {str(e)}"


def get_publishable_key():
    """Retorna la publishable key para el frontend."""
    return get_stripe_config()["publishable_key"]
