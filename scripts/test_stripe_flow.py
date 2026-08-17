#!/usr/bin/env python3
"""Test Stripe checkout - complete flow."""
import sys, os, json, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from cerebro.server import load_dotenv
load_dotenv()

BASE = "http://localhost:8000"


def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"HTTP Error {e.code}: {error_body}")
        raise


def main():
    from dep_operaciones import gestor_pagos, gestor_ordenes

    admin_secret = os.environ.get("SKILLTWIN_ADMIN_SECRET", "")
    token_resp = api("POST", "/api/auth/token", {"secret": admin_secret})
    token = token_resp["token"]
    print("[1] Admin token obtained")

    orden_data = {
        "cliente_email": "test@stripe.com",
        "clon_id": "rsanchez_cobol",
        "cantidad_horas": 3,
        "descripcion_proyecto": "Test Stripe Checkout",
        "requiere_contrato": True
    }
    result = api("POST", "/api/crear-orden", orden_data, token)
    orden_id = result["orden_id"]
    print(f"[2] Orden creada: {orden_id}")

    factura_id, factura = gestor_pagos.crear_factura(
        orden_id=orden_id,
        cliente_email="test@stripe.com",
        monto_total=75.00,
        comision=11.25,
        cantidad_horas=3,
        tarifa_hora=21.25,
        descripcion_proyecto="Test Stripe Checkout"
    )
    gestor_ordenes.actualizar_pago_orden(orden_id, factura_id, "pendiente")
    print(f"[3] Factura creada: {factura_id} (${factura['monto_total']})")

    print("\n=== CREATING CHECKOUT SESSION ===")
    checkout_data = {"factura_id": factura_id, "orden_id": orden_id}
    checkout = api("POST", "/api/stripe/create-checkout", checkout_data, token)
    checkout_url = checkout.get("url", "")
    print("[4] Checkout creado!")
    print(f"    URL: {checkout_url[:100]}...")

    with open("test_stripe_url.txt", "w", encoding="utf-8") as f:
        f.write(checkout_url)
    with open("test_orden_id.txt", "w", encoding="utf-8") as f:
        f.write(orden_id)
    with open("test_factura_id.txt", "w", encoding="utf-8") as f:
        f.write(factura_id)

    print("\n=== INSTRUCCIONES PARA PROBAR ===")
    print("1. Abre esta URL en tu navegador:")
    print(f"   {checkout_url}")
    print("\n2. Tarjeta de prueba: 4242 4242 4242 4242")
    print("3. Fecha: cualquier fecha futura")
    print("4. CVC: 123")
    print("5. Email: cualquier email")
    print("\n6. Después del pago, verifica con:")
    print("   python test_stripe_verify.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
