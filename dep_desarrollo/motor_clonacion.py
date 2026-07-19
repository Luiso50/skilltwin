import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
import threading

# Soporte para JSON (legacy) y SQLite (nuevo)
USE_SQLITE = os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"

DB_FILE = os.path.join(os.path.dirname(__file__), "clones_db.json")
db_lock = threading.RLock()

if USE_SQLITE:
    try:
        from dep_operaciones.database import cargar_clones as db_cargar_clones
        from dep_operaciones.database import guardar_clone as db_guardar_clone
        from dep_operaciones.database import obtener_clone as db_obtener_clone
        from dep_operaciones.database import init_database
        init_database()
    except ImportError:
        USE_SQLITE = False


def inicializar_db():
    """Crea el archivo JSON de base de datos si no existe (solo modo JSON)."""
    if USE_SQLITE:
        return
        
    with db_lock:
        if not os.path.exists(DB_FILE):
            datos_iniciales = {
                "clones": {
                    "rsanchez_cobol": {
                        "nombre": "Roberto Sánchez",
                        "especialidad": "Programador Senior de COBOL",
                        "conocimiento": "La estructura básica de un programa COBOL consta de cuatro divisiones obligatorias: IDENTIFICATION DIVISION, ENVIRONMENT DIVISION, DATA DIVISION y PROCEDURE DIVISION. Para optimizar el rendimiento de procesos batch, siempre es mejor usar sentencias PERFORM en lugar de bucles anidados complejos, y evitar a toda costa el uso de GOTO. Los archivos secuenciales indexados se definen en the FILE-CONTROL bajo la ENVIRONMENT DIVISION.",
                        "fecha_creacion": "2026-07-04"
                    },
                    "ana_finanzas": {
                        "nombre": "Ana Gómez",
                        "especialidad": "Asesora de Finanzas Personales",
                        "conocimiento": "La regla de oro del ahorro es la fórmula 50/30/20: 50% para necesidades básicas (vivienda, comida), 30% para deseos y entretenimiento, y 20% destinado al ahorro o pago de deudas. Antes de invertir, siempre se debe construir un fondo de emergencia que cubra entre 3 y 6 meses de gastos fijos en un activo líquido y de bajo riesgo.",
                        "fecha_creacion": "2026-07-04"
                    }
                }
            }
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)


def cargar_datos():
    """Carga todos los datos de clones."""
    if USE_SQLITE:
        clones = db_cargar_clones()
        return {"clones": clones}
    
    with db_lock:
        inicializar_db()
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_datos(datos):
    """Guarda todos los datos de clones."""
    if USE_SQLITE:
        for clon_id, clon_data in datos.get("clones", {}).items():
            db_guardar_clone(
                clon_id,
                clon_data["nombre"],
                clon_data["especialidad"],
                clon_data["conocimiento"]
            )
        return
    
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)


def crear_clon(id_clon, nombre, especialidad, conocimiento):
    """Registra y entrena a un nuevo clon digital."""
    if USE_SQLITE:
        existing = db_obtener_clone(id_clon)
        if existing:
            print(f"\n⚠️ El identificador '{id_clon}' ya existe. Intenta con otro.")
            return False
        db_guardar_clone(id_clon, nombre, especialidad, conocimiento)
        print(f"\n✅ ¡Clon digital '{nombre}' ({especialidad}) creado con éxito!")
        return True
    
    datos = cargar_datos()
    
    if id_clon in datos["clones"]:
        print(f"\n⚠️ El identificador '{id_clon}' ya existe. Intenta con otro.")
        return False
        
    datos["clones"][id_clon] = {
        "nombre": nombre,
        "especialidad": especialidad,
        "conocimiento": conocimiento,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d")
    }
    guardar_datos(datos)
    print(f"\n✅ ¡Clon digital '{nombre}' ({especialidad}) creado con éxito!")
    return True


def consultar_clon_offline(clon, pregunta):
    """Responde de forma simulada buscando palabras clave si no hay API Key."""
    conocimiento = clon["conocimiento"]
    especialidad = clon["especialidad"]
    nombre = clon["nombre"]
    
    # Búsqueda simple de palabras clave para dar respuestas contextuales básicas
    pregunta_normalizada = pregunta.lower()
    palabras_clave = [p.strip() for p in pregunta_normalizada.split(" ")]
    
    match_sentences = []
    oraciones = conocimiento.split(". ")
    for oracion in oraciones:
        for pal in palabras_clave:
            if len(pal) > 3 and pal in oracion.lower() and oracion not in match_sentences:
                match_sentences.append(oracion)
                
    if match_sentences:
        respuesta = " ".join(match_sentences)
    else:
        # Respuesta por defecto basada en el conocimiento
        respuesta = conocimiento[:150] + "..."

    return (
        f"[MODO OFFLINE - clon de {nombre}]\n"
        f"Hola, soy el clon digital de {nombre}, especialista en {especialidad}.\n"
        f"Basado en mi conocimiento: \"{respuesta}\"\n"
        f"(Configura la variable de entorno GEMINI_API_KEY para respuestas inteligentes de IA)."
    )


def consultar_clon_online(clon, pregunta, api_key):
    """Consulta al clon enviando su base de conocimiento a Gemini a través de HTTP directo."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = (
        f"Eres el clon digital de {clon['nombre']}, experto en {clon['especialidad']}.\n"
        f"Tu base de conocimiento es la siguiente:\n"
        f"\"\"\"\n{clon['conocimiento']}\n\"\"\"\n\n"
        f"Instrucción: Responde a la pregunta del usuario utilizando de forma estricta y profesional "
        f"tu base de conocimiento. Si la pregunta no se relaciona con tu conocimiento o especialidad, "
        f"responde amablemente diciendo que esa consulta está fuera de tu campo de especialización.\n\n"
        f"Pregunta del usuario: {pregunta}\n"
        f"Respuesta del clon:"
    )
    
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(body).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )
        with urllib.request.urlopen(req) as response:  # nosec B310
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"Error al conectar con la API de Gemini: {e}\nCausa: Asegúrate de que tu GEMINI_API_KEY sea correcta."


def consultar_clon(id_clon, pregunta):
    """Orquesta la consulta decidiendo si usa el modo online u offline."""
    datos = cargar_datos()
    if id_clon not in datos["clones"]:
        print(f"\n❌ El clon '{id_clon}' no existe.")
        return None
        
    clon = datos["clones"][id_clon]
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        return consultar_clon_online(clon, pregunta, api_key)
    else:
        return consultar_clon_offline(clon, pregunta)


def menu():
    inicializar_db()
    while True:
        print("\n" + "="*45)
        print("    SKILLTWIN MOTOR DE CLONACIÓN v1.0")
        print("="*45)
        print("1. Ver clones creados")
        print("2. Registrar / Entrenar nuevo clon")
        print("3. Consultar a un clon digital")
        print("4. Salir")
        
        opcion = input("\nSelecciona una opción (1-4): ").strip()
        
        if opcion == "1":
            datos = cargar_datos()
            print("\n--- CLONES REGISTRADOS EN LA PLATAFORMA ---")
            for cid, info in datos["clones"].items():
                print(f"- ID: {cid} | Nombre: {info['nombre']} | Especialidad: {info['especialidad']}")
                
        elif opcion == "2":
            print("\n--- REGISTRAR NUEVA HABILIDAD ---")
            id_clon = input("ID único del clon (ej. juan_seo): ").strip().lower()
            nombre = input("Nombre completo del profesional: ").strip()
            especialidad = input("Especialidad del clon: ").strip()
            print("Escribe o pega la base de conocimiento (máx. 1000 palabras):")
            conocimiento = input("> ").strip()
            
            if id_clon and nombre and especialidad and conocimiento:
                crear_clon(id_clon, nombre, especialidad, conocimiento)
            else:
                print("\n⚠️ Todos los campos son obligatorios.")
                
        elif opcion == "3":
            datos = cargar_datos()
            print("\n--- SELECCIONA UN CLON PARA CONSULTAR ---")
            clones_disponibles = list(datos["clones"].keys())
            for idx, cid in enumerate(clones_disponibles, 1):
                print(f"{idx}. {cid} ({datos['clones'][cid]['especialidad']})")
                
            sel = input("\nSelecciona el número del clon: ").strip()
            try:
                clon_idx = int(sel) - 1
                if 0 <= clon_idx < len(clones_disponibles):
                    id_clon = clones_disponibles[clon_idx]
                    pregunta = input(f"\nPregunta para el clon de {id_clon}: ").strip()
                    if pregunta:
                        print("\n[Pensando...]")
                        respuesta = consultar_clon(id_clon, pregunta)
                        print(f"\nRespuesta:\n{respuesta}")
                else:
                    print("\n⚠️ Selección inválida.")
            except ValueError:
                print("\n⚠️ Debe ingresar un número.")
                
        elif opcion == "4":
            print("\n¡Gracias por usar SkillTwin! Cerrando motor de desarrollo...")
            break
        else:
            print("\n⚠️ Opción no válida. Inténtalo de nuevo.")


if __name__ == "__main__":
    menu()
