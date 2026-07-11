import os
import json
from datetime import datetime, timedelta

DB_FINANZAS = os.path.join(os.path.dirname(__file__), "finanzas_db.json")

def inicializar_finanzas():
    """Crea la base de datos financiera si no existe, con datos iniciales realistas."""
    if not os.path.exists(DB_FINANZAS):
        hoy = datetime.now()
        fecha_futura_1 = (hoy + timedelta(days=2)).strftime("%Y-%m-%d")
        fecha_futura_2 = (hoy + timedelta(days=5)).strftime("%Y-%m-%d")
        fecha_vencida = (hoy - timedelta(days=4)).strftime("%Y-%m-%d")

        datos_iniciales = {
            "flujo_caja": {
                "2026-05": {
                    "ingresos_plan": 1500.0,
                    "ingresos_real": 1420.0,
                    "egresos_plan": 600.0,
                    "egresos_real": 620.0
                },
                "2026-06": {
                    "ingresos_plan": 2200.0,
                    "ingresos_real": 2450.0,
                    "egresos_plan": 800.0,
                    "egresos_real": 780.0
                },
                "2026-07": {
                    "ingresos_plan": 3500.0,
                    "ingresos_real": 1200.0,  # A mitad de mes
                    "egresos_plan": 1200.0,
                    "egresos_real": 950.0
                }
            },
            "cuentas_cobrar": [
                {
                    "id": "FAC-001",
                    "cliente": "Banco del Norte (Alquiler Clon COBOL)",
                    "monto": 850.0,
                    "vencimiento": fecha_vencida,
                    "estado": "Pendiente"
                },
                {
                    "id": "FAC-002",
                    "cliente": "Consultora Tecno (Alquiler Clon Legal IA)",
                    "monto": 1200.0,
                    "vencimiento": fecha_futura_2,
                    "estado": "Pendiente"
                },
                {
                    "id": "FAC-003",
                    "cliente": "Startup Alpha (Asesoría Finanzas)",
                    "monto": 400.0,
                    "vencimiento": (hoy - timedelta(days=10)).strftime("%Y-%m-%d"),
                    "estado": "Cobrado"
                }
            ],
            "cuentas_pagar": [
                {
                    "id": "PROV-001",
                    "proveedor": "OpenAI / Gemini API (Infraestructura)",
                    "monto": 350.0,
                    "vencimiento": fecha_futura_1,
                    "estado": "Pendiente"
                },
                {
                    "id": "PROV-002",
                    "proveedor": "Servidores Cloud AWS",
                    "monto": 150.0,
                    "vencimiento": (hoy + timedelta(days=12)).strftime("%Y-%m-%d"),
                    "estado": "Pendiente"
                },
                {
                    "id": "PROV-003",
                    "proveedor": "Desarrollador Freelance (Soporte)",
                    "monto": 500.0,
                    "vencimiento": (hoy - timedelta(days=1)).strftime("%Y-%m-%d"),
                    "estado": "Pagado"
                }
            ]
        }
        with open(DB_FINANZAS, "w", encoding="utf-8") as f:
            json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)

def cargar_finanzas():
    inicializar_finanzas()
    with open(DB_FINANZAS, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_finanzas(datos):
    with open(DB_FINANZAS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def mostrar_flujo_caja():
    """Muestra la tabla de comparación Plan vs Real."""
    datos = cargar_finanzas()
    print("\n" + "="*70)
    print("                 ESTADO DE FLUJO DE CAJA (PLAN vs REAL)")
    print("="*70)
    print(f"{'Mes':<10} | {'Ing. Plan':<12} | {'Ing. Real':<12} | {'Egr. Plan':<12} | {'Egr. Real':<12}")
    print("-"*70)
    
    for mes, valores in sorted(datos["flujo_caja"].items()):
        print(f"{mes:<10} | ${valores['ingresos_plan']:<11.2f} | ${valores['ingresos_real']:<11.2f} | ${valores['egresos_plan']:<11.2f} | ${valores['egresos_real']:<11.2f}")
    
    print("="*70)

def mostrar_calendario_y_alertas():
    """Genera alertas y muestra las fechas de cobro y pago ordenadas cronológicamente."""
    datos = cargar_finanzas()
    hoy = datetime.now().date()
    
    eventos = []
    alertas = []
    
    # Cargar cobros pendientes
    for c in datos["cuentas_cobrar"]:
        if c["estado"] == "Pendiente":
            fecha_venc = datetime.strptime(c["vencimiento"], "%Y-%m-%d").date()
            dias_dif = (fecha_venc - hoy).days
            eventos.append({
                "tipo": "COBRO",
                "id": c["id"],
                "entidad": c["cliente"],
                "monto": c["monto"],
                "fecha": fecha_venc,
                "dias": dias_dif
            })
            if dias_dif < 0:
                alertas.append(f"[CRITICO] COBRO VENCIDO hace {abs(dias_dif)} dias: {c['id']} de {c['cliente']} (${c['monto']})")
                
    # Cargar pagos pendientes
    for p in datos["cuentas_pagar"]:
        if p["estado"] == "Pendiente":
            fecha_venc = datetime.strptime(p["vencimiento"], "%Y-%m-%d").date()
            dias_dif = (fecha_venc - hoy).days
            eventos.append({
                "tipo": "PAGO",
                "id": p["id"],
                "entidad": p["proveedor"],
                "monto": p["monto"],
                "fecha": fecha_venc,
                "dias": dias_dif
            })
            if dias_dif < 0:
                alertas.append(f"[ALERTA] PAGO VENCIDO hace {abs(dias_dif)} dias: {p['id']} a {p['proveedor']} (${p['monto']})")
            elif 0 <= dias_dif <= 3:
                alertas.append(f"[ATENCION] Pago proximo a vencer ({dias_dif} dias): {p['id']} a {p['proveedor']} (${p['monto']})")

    # Mostrar Alertas primero
    print("\n" + "="*70)
    print("                         ALERTAS FINANCIERAS")
    print("="*70)
    if alertas:
        for al in alertas:
            print(f" {al}")
    else:
        print(" Sin alertas criticas. Finanzas en orden estable.")
    print("="*70)

    # Mostrar Calendario Cronológico
    print("\n" + "="*70)
    print("                 CALENDARIO DE VENCIMIENTOS (PROXIMOS)")
    print("="*70)
    print(f"{'Fecha':<12} | {'Tipo':<8} | {'ID':<10} | {'Monto':<10} | {'Entidad/Concepto'}")
    print("-"*70)
    
    # Ordenar por fecha de vencimiento
    eventos_ordenados = sorted(eventos, key=lambda x: x["fecha"])
    for ev in eventos_ordenados:
        status_plazo = f"({ev['dias']} dias)" if ev['dias'] >= 0 else "(VENCIDO)"
        print(f"{ev['fecha'].strftime('%Y-%m-%d'):<12} | {ev['tipo']:<8} | {ev['id']:<10} | ${ev['monto']:<9.2f} | {ev['entidad']} {status_plazo}")
    
    print("="*70)

def registrar_transaccion():
    """Permite ingresar nuevos cobros o pagos al sistema."""
    datos = cargar_finanzas()
    print("\n--- REGISTRAR MOVIMIENTO FINANCIERO ---")
    print("1. Agregar Cuenta por Cobrar (Factura a Cliente)")
    print("2. Agregar Cuenta por Pagar (Gasto a Proveedor)")
    
    op = input("\nSelecciona tipo (1-2): ").strip()
    if op not in ["1", "2"]:
        print("Operacion cancelada. Opcion invalida.")
        return
        
    ident = input("Codigo de referencia (ej. FAC-004 o PROV-005): ").strip().upper()
    nombre = input("Entidad (Cliente o Proveedor): ").strip()
    try:
        monto = float(input("Monto en USD: ").strip())
    except ValueError:
        print("Monto no valido.")
        return
        
    venc = input("Fecha de vencimiento (YYYY-MM-DD): ").strip()
    try:
        datetime.strptime(venc, "%Y-%m-%d")
    except ValueError:
        print("Formato de fecha incorrecto. Debe ser YYYY-MM-DD.")
        return

    if op == "1":
        datos["cuentas_cobrar"].append({
            "id": ident,
            "cliente": nombre,
            "monto": monto,
            "vencimiento": venc,
            "estado": "Pendiente"
        })
        print(f"\n[OK] Cuenta por cobrar {ident} registrada.")
    else:
        datos["cuentas_pagar"].append({
            "id": ident,
            "proveedor": nombre,
            "monto": monto,
            "vencimiento": venc,
            "estado": "Pendiente"
        })
        print(f"\n[OK] Cuenta por pagar {ident} registrada.")
        
    guardar_finanzas(datos)

def conciliar_estado():
    """Marca un cobro como recibido o un pago como realizado y actualiza el flujo de caja real."""
    datos = cargar_finanzas()
    print("\n--- REGISTRAR COBRO O PAGO EFECTIVO ---")
    print("1. Marcar Cuenta por Cobrar como COBRADA")
    print("2. Marcar Cuenta por Pagar como PAGADA")
    
    op = input("\nSelecciona accion (1-2): ").strip()
    mes_actual = datetime.now().strftime("%Y-%m")
    
    if op == "1":
        pendientes = [c for c in datos["cuentas_cobrar"] if c["estado"] == "Pendiente"]
        if not pendientes:
            print("No hay cobros pendientes.")
            return
        for idx, c in enumerate(pendientes, 1):
            print(f"{idx}. {c['id']} - {c['cliente']} | ${c['monto']}")
        
        sel = input("\nSelecciona el numero de factura cobrada: ").strip()
        try:
            c_idx = int(sel) - 1
            if 0 <= c_idx < len(pendientes):
                factura = pendientes[c_idx]
                # Modificar estado en la lista original
                for orig in datos["cuentas_cobrar"]:
                    if orig["id"] == factura["id"]:
                        orig["estado"] = "Cobrado"
                
                # Sumar al flujo de caja real del mes actual
                if mes_actual not in datos["flujo_caja"]:
                    datos["flujo_caja"][mes_actual] = {"ingresos_plan": 0.0, "ingresos_real": 0.0, "egresos_plan": 0.0, "egresos_real": 0.0}
                datos["flujo_caja"][mes_actual]["ingresos_real"] += factura["monto"]
                
                print(f"\n[OK] Factura {factura['id']} cobrada. ${factura['monto']} agregados al flujo real de {mes_actual}.")
            else:
                print("Seleccion no valida.")
        except ValueError:
            print("Ingreso no valido.")
            
    elif op == "2":
        pendientes = [p for p in datos["cuentas_pagar"] if p["estado"] == "Pendiente"]
        if not pendientes:
            print("No hay pagos pendientes.")
            return
        for idx, p in enumerate(pendientes, 1):
            print(f"{idx}. {p['id']} - {p['proveedor']} | ${p['monto']}")
            
        sel = input("\nSelecciona el numero de gasto pagado: ").strip()
        try:
            p_idx = int(sel) - 1
            if 0 <= p_idx < len(pendientes):
                gasto = pendientes[p_idx]
                for orig in datos["cuentas_pagar"]:
                    if orig["id"] == gasto["id"]:
                        orig["estado"] = "Pagado"
                        
                # Sumar al flujo de caja real del mes actual
                if mes_actual not in datos["flujo_caja"]:
                    datos["flujo_caja"][mes_actual] = {"ingresos_plan": 0.0, "ingresos_real": 0.0, "egresos_plan": 0.0, "egresos_real": 0.0}
                datos["flujo_caja"][mes_actual]["egresos_real"] += gasto["monto"]
                
                print(f"\n[OK] Pago {gasto['id']} realizado. ${gasto['monto']} deducidos en el flujo real de {mes_actual}.")
            else:
                print("Seleccion no valida.")
        except ValueError:
            print("Ingreso no valido.")
            
    guardar_finanzas(datos)

def dar_sugerencias():
    """Genera recomendaciones financieras automatizadas basadas en los desfases y alertas."""
    datos = cargar_finanzas()
    print("\n" + "="*70)
    print("                 SUGERENCIAS Y ANALISIS FINANCIERO")
    print("="*70)
    
    # 1. Analizar desfase plan vs real
    mes_actual = datetime.now().strftime("%Y-%m")
    if mes_actual in datos["flujo_caja"]:
        flujo = datos["flujo_caja"][mes_actual]
        ingreso_diff = flujo["ingresos_real"] - flujo["ingresos_plan"]
        
        print(f" Analisis del mes en curso ({mes_actual}):")
        print(f"  - Tus ingresos reales estan en ${flujo['ingresos_real']:.2f} vs ${flujo['ingresos_plan']:.2f} planificados.")
        if ingreso_diff < 0:
            print(f"  [!] Alerta de Liquidez: Tienes un deficit de ${abs(ingreso_diff):.2f} contra tu plan original.")
            print(f"      Recomendacion: Ejecuta llamadas de cobro para las facturas pendientes de este mes.")
        else:
            print("  [+] Superavit: El rendimiento de ingresos supera la meta planificada.")

    # 2. Recomendaciones de cobros/pagos
    cobros_pendientes = sum(c["monto"] for c in datos["cuentas_cobrar"] if c["estado"] == "Pendiente")
    pagos_pendientes = sum(p["monto"] for p in datos["cuentas_pagar"] if p["estado"] == "Pendiente")
    
    print(f"\n Balance de Saldos Pendientes:")
    print(f"  - Total por cobrar: ${cobros_pendientes:.2f}")
    print(f"  - Total por pagar:  ${pagos_pendientes:.2f}")
    
    if pagos_pendientes > cobros_pendientes:
        print("  [ATENCION] Tus cuentas por pagar superan a las cuentas por cobrar pendientes.")
        print("  Recomendacion: Negocia un plazo de gracia con proveedores o incentiva a clientes a pagar antes ofreciendo un 2% de descuento por pronto pago.")
    else:
        print("  [OK] El saldo por cobrar cubre holgadamente tus obligaciones inmediatas.")
        
    print("\n Sugerencias de Comision en SkillTwin:")
    print("  - Mantener la comision base del 15% sobre alquiler de clones.")
    print("  - Si el costo de consumo de APIs (OpenAI/Gemini) sube un 10%, aumentar la comision de transaccion al 18% para no diluir el margen operativo.")
    print("="*70)

def menu():
    inicializar_finanzas()
    while True:
        print("\n" + "="*45)
        print("    SKILLTWIN GESTION FINANCIERA v1.0")
        print("="*45)
        print("1. Ver Flujo de Caja (Plan vs Real)")
        print("2. Ver Calendario de Vencimientos y Alertas")
        print("3. Registrar Cuenta por Cobrar / Pagar")
        print("4. Conciliar Transaccion (Cobrar/Pagar)")
        print("5. Obtener Sugerencias Financieras")
        print("6. Salir")
        
        op = input("\nSelecciona una opcion (1-6): ").strip()
        
        if op == "1":
            mostrar_flujo_caja()
        elif op == "2":
            mostrar_calendario_y_alertas()
        elif op == "3":
            registrar_transaccion()
        elif op == "4":
            conciliar_estado()
        elif op == "5":
            dar_sugerencias()
        elif op == "6":
            print("\nCerrando modulo financiero. Operaciones guardadas.")
            break
        else:
            print("\nOpcion no valida.")

if __name__ == "__main__":
    menu()
