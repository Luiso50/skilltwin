import os
import json
import urllib.request
import urllib.parse
import re
import html  # Importación corregida para unescape
from datetime import datetime

REPORT_FILE = os.path.join(os.path.dirname(__file__), "reporte_inteligencia.json")

def buscar_en_internet(query):
    """Busca en DuckDuckGo HTML de forma real y extrae resúmenes sin librerías externas."""
    print(f"\n[BUSQUEDA] [Agente de Investigacion] Buscando en la web: '{query}'...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            # Buscar fragmentos de texto en los resultados de DuckDuckGo HTML
            snippets = re.findall(r'class=["\']result__snippet["\'][^>]*>(.*?)</a>', html_content, re.DOTALL)
            resultados = []
            for s in snippets[:4]:
                # Limpiar etiquetas HTML residuales
                texto_limpio = re.sub(r'<[^>]+>', '', s).strip()
                texto_limpio = html.unescape(texto_limpio)
                # Reemplazo manual básico de caracteres HTML comunes
                texto_limpio = texto_limpio.replace("&amp;", "&").replace("&quot;", '"').replace("&#x27;", "'")
                resultados.append(texto_limpio)
            return resultados
    except Exception as e:
        print(f"[ALERTA] Error al conectar con internet: {e}. Usando base de datos interna de respaldo.")
        return [
            "Tendencia: Gran escasez de expertos en mantenimiento de bases de datos COBOL legadas en banca.",
            "Demanda: Crecimiento del 200% en solicitudes de consultoría sobre cumplimiento regulatorio de IA (AI Act).",
            "Saturación: Los redactores de contenido generalista de IA están saturando el mercado; baja rentabilidad."
        ]

def analizar_datos_con_gemini(datos_busqueda, nicho, api_key):
    """Utiliza Gemini para sintetizar los hallazgos y proponer una estrategia de ventas."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    contexto = "\n".join([f"- {d}" for d in datos_busqueda])
    prompt = (
        f"Eres el 'Agente de Inteligencia de Mercado y Ventas' de SkillTwin.\n"
        f"Hemos realizado una investigación web sobre el nicho '{nicho}'. Aquí están los resultados de búsqueda recopilados:\n"
        f"\"\"\"\n{contexto}\n\"\"\"\n\n"
        f"Tu tarea consiste en:\n"
        f"1. Analizar si el nicho '{nicho}' tiene demanda real y potencial para SkillTwin (monetizar gemelos digitales de expertos).\n"
        f"2. Generar un reporte corto indicando el público objetivo (empresas que sufren por falta de este talento).\n"
        f"3. Redactar una propuesta comercial de correo frío (cold email) hiper-personalizada dirigida a un director de tecnología (CTO) o gerente de esa área. Explica cómo alquilar un 'clon digital de un experto de SkillTwin' les ahorraría un 70% en costos de contratación.\n\n"
        f"Entrega tu respuesta estructurada en formato JSON con la siguiente estructura exacta:\n"
        f"{{\n"
        f"  \"analisis_oportunidad\": \"resumen del análisis de demanda\",\n"
        f"  \"empresas_objetivo\": [\"Tipo de empresa 1\", \"Tipo de empresa 2\"],\n"
        f"  \"correo_ventas\": \"Contenido del correo redactado de forma persuasiva\"\n"
        f"}}"
    )
    
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(body).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            json_response = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(json_response)
    except Exception as e:
        print(f"[ALERTA] Error al procesar con la IA: {e}")
        return None

def analizar_datos_offline(datos_busqueda, nicho):
    """Fallback offline en caso de que no haya API Key."""
    return {
        "analisis_oportunidad": f"El nicho '{nicho}' muestra un interes medio/alto segun la simulacion local. Existe una clara oportunidad debido a la escasez de profesionales fisicos en esta especialidad.",
        "empresas_objetivo": [
            "Bancos e instituciones financieras tradicionales",
            "Consultoras de tecnologia en plena transformacion digital",
            "Pymes que buscan automatizar asesorias sin contratar personal full-time"
        ],
        "correo_ventas": (
            f"Asunto: Solucion inmediata a la escasez de talento en {nicho}\n\n"
            f"Estimado Director,\n\n"
            f"Le escribo desde SkillTwin. Sabemos que encontrar profesionales expertos en {nicho} es costoso y lento.\n"
            f"Hemos creado un 'Gemelo Digital' interactivo de un experto senior en esta area, entrenado con su conocimiento especifico.\n"
            f"Su empresa puede 'alquilar' este clon de IA por una fraccion del costo tradicional para responder consultas especializadas 24/7.\n\n"
            f"¿Le gustaria una demostracion rapida de 5 minutos?\n\n"
            f"Atentamente,\nAgente de Ventas de SkillTwin"
        )
    }

def ejecutar_inteligencia_ventas(nicho):
    """Orquesta la investigación de mercado, el análisis y la creación de la estrategia de venta."""
    print(f"\n[VENTAS] [Agente de Ventas] Iniciando ciclo de prospeccion para el nicho: {nicho}...")
    
    # 1. Buscar información del mercado
    query = f"demand for {nicho} skills shortage 2026"
    resultados_web = buscar_en_internet(query)
    
    # 2. Procesar la información (Online u Offline)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        reporte = analizar_datos_con_gemini(resultados_web, nicho, api_key)
        if not reporte:
            reporte = analizar_datos_offline(resultados_web, nicho)
    else:
        reporte = analizar_datos_offline(resultados_web, nicho)
        
    # Guardar reporte para que otros departamentos (como Finanzas u Operaciones) lo usen
    informe_final = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nicho_analizado": nicho,
        "resultados_busqueda_fuente": resultados_web,
        "reporte_ventas": reporte
    }
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(informe_final, f, indent=4, ensure_ascii=False)
        
    print(f"\n[ARCHIVO] Reporte corporativo guardado en: {REPORT_FILE}")
    
    # Mostrar resultados en pantalla
    print("\n" + "="*50)
    print("      INFORME GENERADO POR EL AGENTE DE VENTAS")
    print("="*50)
    print(f"OPORTUNIDAD: {reporte['analisis_oportunidad']}")
    print(f"EMPRESAS OBJETIVO: {', '.join(reporte['empresas_objetivo'])}")
    print(f"\nPROPUESTA DE CORREO REDACTADA:")
    print("-" * 50)
    print(reporte['correo_ventas'])
    print("-" * 50)
    
    return informe_final

if __name__ == "__main__":
    import sys
    nicho_por_defecto = "programacion COBOL en bancos"
    if len(sys.argv) > 1:
        nicho_por_defecto = " ".join(sys.argv[1:])
        
    ejecutar_inteligencia_ventas(nicho_por_defecto)
