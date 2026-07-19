"""
Módulo para generar contratos automáticos usando Gemini AI.
Se integra con el orquestador de órdenes.
"""

import os
import json
import urllib.request
from datetime import datetime, timedelta


def generar_contrato_gemini(orden_id, cliente_email, clon_id, clon_nombre, 
                            especialidad, cantidad_horas, monto_total, comision):
    """
    Genera un contrato legal profesional usando Gemini AI.
    Retorna el texto del contrato.
    """
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Si no hay API key, retornar un contrato por defecto
        return generar_contrato_default(orden_id, cliente_email, clon_nombre, 
                                        especialidad, cantidad_horas, monto_total, comision)
    
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    # Fecha de vencimiento (30 días después)
    fecha_inicio = datetime.now()
    fecha_fin = fecha_inicio + timedelta(days=30)
    
    prompt = f"""
Eres un abogado especializado en contratos de licenciamiento de propiedad intelectual.
Genera un contrato profesional y legal para los siguientes datos:

DATOS DEL CONTRATO:
- ID de Orden: {orden_id}
- Fecha: {fecha_inicio.strftime('%d de %B de %Y')}
- Cliente: {cliente_email}
- Experto (Licenciante): {clon_nombre}
- Especialidad: {especialidad}
- Horas de Servicio: {cantidad_horas} horas
- Tarifa: ${monto_total / cantidad_horas:.2f}/hora
- Total a Pagar: ${monto_total:.2f}
- Comisión de Plataforma: ${comision:.2f}
- Fecha de Vencimiento: {fecha_fin.strftime('%d de %B de %Y')}

Genera un contrato en formato TEXTO que incluya:
1. Encabezado: "CONTRATO DE LICENCIAMIENTO DE SERVICIOS PROFESIONALES"
2. Partes del Contrato (Cliente y Licenciante)
3. Descripción de Servicios
4. Términos y Condiciones
5. Cláusulas de Confidencialidad
6. Cláusulas de Terminación
7. Limitaciones de Responsabilidad
8. Ley Aplicable
9. Firmas (simuladas)

El contrato debe ser profesional, legal y en español. Incluye números de artículos para referencia.
"""
    
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2000,
            "responseMimeType": "text/plain"
        }
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), 
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:  # nosec B310
            res_data = json.loads(response.read().decode("utf-8"))
            contrato_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return contrato_text
    except Exception as e:
        print(f"[GEMINI] Error generando contrato: {e}")
        return generar_contrato_default(orden_id, cliente_email, clon_nombre, 
                                        especialidad, cantidad_horas, monto_total, comision)


def generar_contrato_default(orden_id, cliente_email, clon_nombre, 
                            especialidad, cantidad_horas, monto_total, comision):
    """
    Contrato por defecto si Gemini no está disponible.
    """
    
    fecha_inicio = datetime.now()
    fecha_fin = fecha_inicio + timedelta(days=30)
    
    contrato = f"""
════════════════════════════════════════════════════════════════════════════
                CONTRATO DE LICENCIAMIENTO DE SERVICIOS PROFESIONALES
════════════════════════════════════════════════════════════════════════════

FECHA: {fecha_inicio.strftime('%d de %B de %Y')}
ID DE ORDEN: {orden_id}

PARTES:
1. LICENCIANTE: {clon_nombre}
   - Especialidad: {especialidad}
   - Identificado como: {orden_id}_experto

2. LICENCIATARIO (CLIENTE): {cliente_email}

────────────────────────────────────────────────────────────────────────────
ARTÍCULO 1: OBJETO DEL CONTRATO
────────────────────────────────────────────────────────────────────────────

El Licenciante se compromete a proporcionar servicios profesionales de asesoría 
y consultoría en el área de {especialidad} por un total de {cantidad_horas} horas 
de trabajo.

Los servicios se prestarán de conformidad con los más altos estándares de la 
industria y de acuerdo con la ley aplicable.

────────────────────────────────────────────────────────────────────────────
ARTÍCULO 2: TÉRMINOS ECONÓMICOS
────────────────────────────────────────────────────────────────────────────

- Tarifa por Hora: ${monto_total / cantidad_horas:.2f} USD
- Horas Contratadas: {cantidad_horas} horas
- Monto Total: ${monto_total:.2f} USD
- Comisión de Plataforma: ${comision:.2f} USD (incluida en el total)
- Total a Pagar: ${monto_total:.2f} USD

El pago debe realizarse según las indicaciones de SkillTwin.

────────────────────────────────────────────────────────────────────────────
ARTÍCULO 3: PLAZO
────────────────────────────────────────────────────────────────────────────

Este contrato es válido desde {fecha_inicio.strftime('%d de %B de %Y')} hasta 
{fecha_fin.strftime('%d de %B de %Y')}.

────────────────────────────────────────────────────────────────────────────
ARTÍCULO 4: CONFIDENCIALIDAD
────────────────────────────────────────────────────────────────────────────

Ambas partes se comprometen a mantener en confidencialidad toda la información 
compartida durante la prestación de servicios, excepto cuando lo autorice la ley 
o sea necesario para cumplir obligaciones legales.

────────────────────────────────────────────────────────────────────────────
ARTÍCULO 5: LIMITACIÓN DE RESPONSABILIDAD
────────────────────────────────────────────────────────────────────────────

SkillTwin actúa como plataforma intermediaria. Ni SkillTwin ni el Licenciante 
serán responsables por daños indirectos, incidentales o consecuentes que puedan 
derivarse del uso de los servicios.

────────────────────────────────────────────────────────────────────────────
ARTÍCULO 6: TERMINACIÓN
────────────────────────────────────────────────────────────────────────────

Este contrato puede ser terminado por cualquiera de las partes con notificación 
escrita con 48 horas de anticipación. En caso de terminación anticipada, se 
facturarán solo las horas trabajadas.

────────────────────────────────────────────────────────────────────────────
ARTÍCULO 7: LEY APLICABLE
────────────────────────────────────────────────────────────────────────────

Este contrato se rige por las leyes del país donde SkillTwin está constituida y 
por los términos de servicio de la plataforma SkillTwin.

════════════════════════════════════════════════════════════════════════════

FIRMAS DIGITALES:

Licenciante: {clon_nombre}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
✓ Digitalmente Firmado

Licenciatario: {cliente_email}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
✓ Digitalmente Firmado

SkillTwin (Plataforma)
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
✓ Validado por Sistema

════════════════════════════════════════════════════════════════════════════
"""
    
    return contrato
