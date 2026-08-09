import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
import threading
import uuid
from collections import defaultdict

# Soporte para JSON (legacy) y SQLite (nuevo)
def _use_sqlite():
    return os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1"


USE_SQLITE = _use_sqlite()

DB_FILE = os.path.join(os.path.dirname(__file__), "clones_db.json")
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memories")
db_lock = threading.RLock()

if _use_sqlite():
    try:
        from dep_operaciones.database import cargar_clones as db_cargar_clones
        from dep_operaciones.database import guardar_clone as db_guardar_clone
        from dep_operaciones.database import obtener_clone as db_obtener_clone
        from dep_operaciones.database import init_database
        init_database()
    except ImportError:
        USE_SQLITE = False


class ConversacionMemoria:
    """Sistema de memoria de conversación para clones."""

    def __init__(self, clone_id, session_id=None):
        self.clone_id = clone_id
        self.session_id = session_id or str(uuid.uuid4())
        self.historial = []
        self.contexto = {}
        self.memorias_exito = []
        self._cargar_memoria()

    def _ruta_memoria(self):
        """Retorna la ruta del archivo de memoria para este clon y sesión."""
        os.makedirs(MEMORY_DIR, exist_ok=True)
        return os.path.join(MEMORY_DIR, f"{self.clone_id}_{self.session_id}.json")

    def _cargar_memoria(self):
        """Carga la memoria desde disco si existe."""
        ruta = self._ruta_memoria()
        if os.path.exists(ruta):
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    self.historial = datos.get("historial", [])
                    self.contexto = datos.get("contexto", {})
                    self.memorias_exito = datos.get("memorias_exito", [])
            except Exception:
                pass

    def _guardar_memoria(self):
        """Guarda la memoria en disco."""
        ruta = self._ruta_memoria()
        datos = {
            "clone_id": self.clone_id,
            "session_id": self.session_id,
            "historial": self.historial[-50:],  # Mantener últimas 50 interacciones
            "contexto": self.contexto,
            "memorias_exito": self.memorias_exito[-20:],  # Mantener últimas 20 memorias de éxito
            "ultima_actualizacion": datetime.now().isoformat()
        }
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def agregar_interaccion(self, pregunta, respuesta, exitosa=True, feedback=None):
        """Agrega una interacción al historial."""
        interaccion = {
            "pregunta": pregunta,
            "respuesta": respuesta,
            "timestamp": datetime.now().isoformat(),
            "exitosa": exitosa
        }
        if feedback:
            interaccion["feedback"] = feedback

        self.historial.append(interaccion)
        self.historial = self.historial[-50:]

        # Si fue exitosa, guardar como memoria de éxito
        if exitosa:
            self.memorias_exito.append({
                "pregunta": pregunta,
                "respuesta": respuesta,
                "contexto": self.contexto.copy(),
                "timestamp": datetime.now().isoformat()
            })
            self.memorias_exito = self.memorias_exito[-20:]

        self._actualizar_contexto(pregunta, respuesta)
        self._guardar_memoria()

    def _actualizar_contexto(self, pregunta, respuesta):
        """Actualiza el contexto basado en la interacción."""
        # Detectar temas recurrentes
        palabras_pregunta = set(pregunta.lower().split())

        # Actualizar contador de temas
        if "temas" not in self.contexto:
            self.contexto["temas"] = {}

        for palabra in palabras_pregunta:
            if len(palabra) > 3:  # Ignorar palabras cortas
                self.contexto["temas"][palabra] = self.contexto["temas"].get(palabra, 0) + 1

        # Guardar última pregunta para referencia
        self.contexto["ultima_pregunta"] = pregunta
        self.contexto["ultima_respuesta"] = respuesta
        self.contexto["total_interacciones"] = len(self.historial)

    def obtener_contexto_para_prompt(self):
        """Retorna contexto formateado para incluir en el prompt."""
        if not self.historial:
            return ""

        contexto_parts = []

        # Agregar resumen de conversación reciente
        if len(self.historial) > 0:
            contexto_parts.append("CONTEXTO DE CONVERSACIÓN RECIENTE:")
            for interaccion in self.historial[-3:]:  # Últimas 3 interacciones
                contexto_parts.append(f"- Pregunta: {interaccion['pregunta']}")
                contexto_parts.append(f"  Respuesta: {interaccion['respuesta'][:100]}...")

        # Agregar temas de interés
        if self.contexto.get("temas"):
            temas_ordenados = sorted(
                self.contexto["temas"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            contexto_parts.append("\nTEMAS DE MAYOR INTERÉS:")
            for tema, count in temas_ordenados:
                contexto_parts.append(f"- {tema} ({count} menciones)")

        return "\n".join(contexto_parts)

    def buscar_memorias_similares(self, pregunta, limite=3):
        """Busca memorias de éxito similares a la pregunta actual."""
        if not self.memorias_exito:
            return []

        palabras_pregunta = set(pregunta.lower().split())
        coincidencias = []

        for memoria in self.memorias_exito:
            palabras_memoria = set(memoria["pregunta"].lower().split())
            similitud = len(palabras_pregunta.intersection(palabras_memoria))
            if similitud > 0:
                coincidencias.append((similitud, memoria))

        # Ordenar por similitud y retornar las mejores
        coincidencias.sort(key=lambda x: x[0], reverse=True)
        return [memoria for _, memoria in coincidencias[:limite]]

    def limpiar_memoria(self):
        """Limpia la memoria de la sesión actual."""
        self.historial = []
        self.contexto = {}
        self.memorias_exito = []
        self._guardar_memoria()


class ConocimientoEstructurado:
    """Sistema de conocimiento estructurado para clones."""

    def __init__(self, conocimiento_texto):
        self.texto_original = conocimiento_texto
        self.categorias = {}
        self.conceptos_clave = []
        self._parsear_conocimiento()

    def _parsear_conocimiento(self):
        """Parsea el conocimiento de texto plano a estructura categorizada."""
        # Dividir por oraciones
        oraciones = self.texto_original.split(". ")

        # Categorías predefinidas
        categorias_detectadas = {
            "definiciones": [],
            "mejores_practicas": [],
            "herramientas": [],
            "procesos": [],
            "consejos": []
        }

        # Palabras clave para categorización
        keywords = {
            "definiciones": ["es", "significa", "define", "concepto", "tipo"],
            "mejores_practicas": ["siempre", "mejor", "nunca", "debe", "recomendado"],
            "herramientas": ["usar", "librería", "framework", "herramienta", "software"],
            "procesos": ["paso", "fase", "proceso", "pipeline", "flujo"],
            "consejos": ["consejo", "tip", "truco", "importante", "clave"]
        }

        for oracion in oraciones:
            oracion_lower = oracion.lower()
            categorizada = False

            for categoria, palbrasclave in keywords.items():
                if any(palabra in oracion_lower for palabra in palbrasclave):
                    categorias_detectadas[categoria].append(oracion.strip())
                    categorizada = True
                    break

            if not categorizada:
                # Por defecto, ir a consejos
                categorias_detectadas["consejos"].append(oracion.strip())

        self.categorias = {k: v for k, v in categorias_detectadas.items() if v}

        # Extraer conceptos clave (palabras importantes)
        palabras_importantes = defaultdict(int)
        stopwords = {"el", "la", "los", "las", "un", "una", "de", "del", "al", "en", "con", "por", "para", "se", "que", "es", "y", "o", "a"}

        for oracion in oraciones:
            palabras = oracion.lower().split()
            for palabra in palabras:
                palabra_limpia = ''.join(c for c in palabra if c.isalnum())
                if len(palabra_limpia) > 4 and palabra_limpia not in stopwords:
                    palabras_importantes[palabra_limpia] += 1

        # Tomar las 10 palabras más frecuentes
        self.conceptos_clave = sorted(
            palabras_importantes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

    def obtener_resumen_estructurado(self):
        """Retorna un resumen estructurado del conocimiento."""
        partes = []

        if self.categorias.get("definiciones"):
            partes.append("DEFINICIONES CLAVE:")
            for def_ in self.categorias["definiciones"][:3]:
                partes.append(f"- {def_}")

        if self.categorias.get("mejores_practicas"):
            partes.append("\nMEJORES PRÁCTICAS:")
            for practica in self.categorias["mejores_practicas"][:3]:
                partes.append(f"- {practica}")

        if self.conceptos_clave:
            partes.append("\nCONCEPTOS PRINCIPALES:")
            for concepto, _ in self.conceptos_clave[:5]:
                partes.append(f"- {concepto}")

        return "\n".join(partes) if partes else self.texto_original[:200] + "..."

    @staticmethod
    def _normalizar_palabra(palabra):
        """Normaliza una palabra para matching (elimina plurales y tildes comunes)."""
        p = ''.join(c for c in palabra if c.isalnum())
        p = p.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        # Quitar plurales simples: -es, -s
        if len(p) > 5 and p.endswith('es'):
            p = p[:-2]
        elif len(p) > 4 and p.endswith('s'):
            p = p[:-1]
        return p

    def buscar_informacion_relevante(self, pregunta):
        """Busca información relevante para una pregunta específica."""
        # Normalizar palabras de la pregunta, ignorar palabras cortas (stopwords)
        _STOPWORDS = {"el","la","los","las","un","una","de","del","al","en","con","por",
                      "para","se","que","es","y","o","a","me","mi","tu","su","le","lo",
                      "quiero","necesito","puedo","hacer","como","cual","donde","cuando"}
        palabras_pregunta = {
            self._normalizar_palabra(w)
            for w in pregunta.lower().split()
            if len(w) > 3 and w not in _STOPWORDS
        }
        relevantes = []

        for categoria, oraciones in self.categorias.items():
            for oracion in oraciones:
                palabras_oracion = {
                    self._normalizar_palabra(w)
                    for w in oracion.lower().split()
                    if len(w) > 3
                }
                coincidencias = len(palabras_pregunta.intersection(palabras_oracion))
                if coincidencias > 0:
                    relevantes.append((coincidencias, oracion, categoria))

        relevantes.sort(key=lambda x: x[0], reverse=True)

        return [
            {"texto": texto, "categoria": cat, "relevancia": rel}
            for rel, texto, cat in relevantes[:5]
        ]


def inicializar_db():
    """Crea el archivo JSON de base de datos si no existe (solo modo JSON)."""
    if _use_sqlite():
        return

    with db_lock:
        if not os.path.exists(DB_FILE):
            os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
            datos_iniciales = {
                "clones": {
                    "rsanchez_cobol": {
                        "nombre": "Roberto Sánchez",
                        "especialidad": "Programador Senior de COBOL",
                        "conocimiento": "La estructura básica de un programa COBOL consta de cuatro divisiones obligatorias: IDENTIFICATION DIVISION, ENVIRONMENT DIVISION, DATA DIVISION y PROCEDURE DIVISION. Para optimizar el rendimiento de procesos batch, siempre es mejor usar sentencias PERFORM en lugar de bucles anidados complejos, y evitar a toda costa el uso de GOTO. Los archivos secuenciales indexados se definen en el FILE-CONTROL bajo la ENVIRONMENT DIVISION.",
                        "fecha_creacion": "2026-07-04",
                        "version_conocimiento": 1,
                        "ultima_actualizacion": "2026-07-04"
                    },
                    "ana_finanzas": {
                        "nombre": "Ana Gómez",
                        "especialidad": "Asesora de Finanzas Personales",
                        "conocimiento": "La regla de oro del ahorro es la fórmula 50/30/20: 50% para necesidades básicas (vivienda, comida), 30% para deseos y entretenimiento, y 20% destinado al ahorro o pago de deudas. Antes de invertir, siempre se debe construir un fondo de emergencia que cubra entre 3 y 6 meses de gastos fijos en un activo líquido y de bajo riesgo.",
                        "fecha_creacion": "2026-07-04",
                        "version_conocimiento": 1,
                        "ultima_actualizacion": "2026-07-04"
                    }
                }
            }
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(datos_iniciales, f, indent=4, ensure_ascii=False)


def cargar_datos():
    """Carga todos los datos de clones."""
    if _use_sqlite():
        clones = db_cargar_clones()
        return {"clones": clones}

    with db_lock:
        inicializar_db()
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def guardar_datos(datos):
    """Guarda todos los datos de clones."""
    if _use_sqlite():
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
    if _use_sqlite():
        existing = db_obtener_clone(id_clon)
        if existing:
            print(f"\n[AVISO] El identificador '{id_clon}' ya existe. Intenta con otro.")
            return False
        db_guardar_clone(id_clon, nombre, especialidad, conocimiento)
        print(f"\n[OK] Clon digital '{nombre}' ({especialidad}) creado con exito!")
        return True

    datos = cargar_datos()

    if id_clon in datos["clones"]:
        print(f"\n[AVISO] El identificador '{id_clon}' ya existe. Intenta con otro.")
        return False

    datos["clones"][id_clon] = {
        "nombre": nombre,
        "especialidad": especialidad,
        "conocimiento": conocimiento,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
        "version_conocimiento": 1,
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d")
    }
    guardar_datos(datos)
    print(f"\n✅ ¡Clon digital '{nombre}' ({especialidad}) creado con éxito!")
    return True


def _detectar_intencion(pregunta):
    """Clasifica la intención de la pregunta en: saludo, capacidad o conocimiento."""
    p = pregunta.lower().strip()
    palabras = p.split()

    _SALUDOS = {"hola", "hi", "hello", "hey", "saludos", "buenas"}
    # Frases completas que expresan solicitud de información sobre capacidades
    _CAPACIDAD_FRASES = {
        "qué puedo hacer", "que puedo hacer", "qué puedes hacer", "que puedes hacer",
        "qué sabes", "que sabes", "en qué ayudas", "en que ayudas",
        "cómo funciona", "como funciona", "para qué sirves", "para que sirves",
        "qué haces", "que haces", "qué ofreces", "que ofreces",
        "que puedo hacer aqui", "qué puedo hacer aquí",
    }
    # Palabras sueltas que sólo aplican si la pregunta es muy corta (≤2 palabras)
    _CAPACIDAD_CORTA = {"ayuda", "help", "menu", "menú", "opciones"}

    # Saludo simple (≤4 palabras y contiene palabra de saludo)
    if len(palabras) <= 4 and any(s in p for s in _SALUDOS):
        return "saludo"

    if any(frase in p for frase in _CAPACIDAD_FRASES):
        return "capacidad"

    # Solo clasifica como capacidad si la pregunta tiene ≤2 palabras
    if len(palabras) <= 2 and any(c in palabras for c in _CAPACIDAD_CORTA):
        return "capacidad"

    return "conocimiento"


def consultar_clon_offline(clon, pregunta, session_id=None):
    """Responde usando el conocimiento estructurado del clon, sin volcar metadatos."""
    conocimiento = clon["conocimiento"]
    especialidad = clon["especialidad"]
    nombre = clon["nombre"]

    datos = cargar_datos()
    clon_id = next(
        (cid for cid, cd in datos["clones"].items() if cd["nombre"] == nombre),
        nombre.lower().replace(" ", "_")
    )

    memoria = ConversacionMemoria(clon_id, session_id)
    conocimiento_estructurado = ConocimientoEstructurado(conocimiento)

    es_primera_vez = memoria.contexto.get("total_interacciones", 0) == 0
    intencion = _detectar_intencion(pregunta)

    partes = []

    if intencion == "saludo":
        if es_primera_vez:
            partes.append(f"Hola, soy el clon digital de **{nombre}**, especialista en *{especialidad}*.")
            partes.append("¿En qué puedo asesorarte hoy?")
        else:
            partes.append("¡Hola de nuevo! ¿En qué más puedo ayudarte?")

    elif intencion == "capacidad":
        partes.append(f"Soy el clon digital de **{nombre}** y puedo asesorarte sobre **{especialidad}**.")
        conceptos = [c.capitalize() for c, _ in conocimiento_estructurado.conceptos_clave[:5]]
        if conceptos:
            partes.append("\nAlgunos temas en los que puedo ayudarte:")
            for c in conceptos:
                partes.append(f"  • {c}")
        partes.append("\nHaz tu pregunta y haré mi mejor esfuerzo para responderte.")

    else:  # conocimiento
        info_relevante = conocimiento_estructurado.buscar_informacion_relevante(pregunta)

        if info_relevante:
            _ETIQUETAS = {
                "definiciones": "Información relevante",
                "mejores_practicas": "Mejores prácticas",
                "herramientas": "Herramientas recomendadas",
                "procesos": "Proceso recomendado",
                "consejos": "Puntos clave",
            }
            # Agrupar por categoría, máximo 4 resultados
            por_categoria = {}
            for info in info_relevante[:4]:
                cat = info["categoria"]
                por_categoria.setdefault(cat, []).append(info["texto"])

            for cat, textos in por_categoria.items():
                partes.append(f"**{_ETIQUETAS.get(cat, cat.capitalize())}:**")
                for t in textos:
                    partes.append(f"• {t}")
                partes.append("")

            # Referencia al contexto previo si existe
            if memoria.historial:
                ultima_pregunta = memoria.historial[-1]["pregunta"]
                if ultima_pregunta.lower() != pregunta.lower():
                    partes.append(
                        f"_Anteriormente hablamos sobre: «{ultima_pregunta}». "
                        "Si quieres profundizar en algún punto, pregúntame._"
                    )
        else:
            # La pregunta no coincide con el conocimiento del clon
            partes.append(
                f"Mi especialidad es **{especialidad}** y no tengo información específica "
                f"sobre «{pregunta}» en mi base de conocimiento."
            )
            # Ofrecer lo que sí sabe
            resumen = conocimiento_estructurado.obtener_resumen_estructurado()
            if resumen:
                partes.append("\nLo que sí puedo ofrecerte dentro de mi especialidad:")
                partes.append(resumen[:400])

    partes.append("\n_(Modo offline · Configura GEMINI_API_KEY para respuestas con IA avanzada)_")

    respuesta_completa = "\n".join(filter(None, partes))
    memoria.agregar_interaccion(pregunta, respuesta_completa, exitosa=True)

    return respuesta_completa


def consultar_clon_online(clon, pregunta, api_key, session_id=None):
    """Consulta al clon con contexto de memoria y conocimiento estructurado."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    nombre = clon["nombre"]
    especialidad = clon["especialidad"]
    conocimiento = clon["conocimiento"]

    # Obtener el ID del clon
    clon_id = None
    datos = cargar_datos()
    for cid, cdata in datos["clones"].items():
        if cdata["nombre"] == nombre:
            clon_id = cid
            break

    if not clon_id:
        clon_id = nombre.lower().replace(" ", "_")

    # Crear o cargar memoria de conversación
    memoria = ConversacionMemoria(clon_id, session_id)

    # Analizar conocimiento estructurado
    conocimiento_estructurado = ConocimientoEstructurado(conocimiento)
    resumen_estructurado = conocimiento_estructurado.obtener_resumen_estructurado()

    # Obtener contexto de conversación
    contexto_conversacion = memoria.obtener_contexto_para_prompt()

    # Buscar memorias de éxito similares
    memorias_similares = memoria.buscar_memorias_similares(pregunta)

    # Construir prompt mejorado
    prompt_parts = [
        f"Eres el clon digital de {nombre}, experto en {especialidad}.",
        "\nTu base de conocimiento estructurado es:",
        f"\"\"\"\n{resumen_estructurado}\n\"\"\"",
        "\nTu conocimiento completo es:",
        f"\"\"\"\n{conocimiento}\n\"\"\""
    ]

    if contexto_conversacion:
        prompt_parts.append(f"\n{contexto_conversacion}")

    if memorias_similares:
        prompt_parts.append("\nMEMORIAS DE RESPUESTAS EXITOSAS ANTERIORES:")
        for memoria_sim in memorias_similares[:2]:
            prompt_parts.append(f"- Pregunta: {memoria_sim['pregunta']}")
            prompt_parts.append(f"  Respuesta exitosa: {memoria_sim['respuesta'][:200]}")

    prompt_parts.extend([
        "\nInstrucción: Responde a la pregunta del usuario utilizando tu conocimiento.",
        "Si es relevante, referencia interacciones anteriores de esta conversación.",
        "Si la pregunta no se relaciona con tu especialidad, indica que está fuera de tu campo.",
        f"\nPregunta del usuario: {pregunta}",
        "\nRespuesta del clon:"
    ])

    prompt = "\n".join(prompt_parts)

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
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
        with urllib.request.urlopen(req, timeout=15) as response:  # nosec B310
            res_data = json.loads(response.read().decode("utf-8"))
            respuesta = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Guardar interacción exitosa en memoria
            memoria.agregar_interaccion(pregunta, respuesta, exitosa=True)

            return respuesta
    except Exception as e:
        error_msg = f"Error al conectar con la API de Gemini: {e}\nCausa: Asegúrate de que tu GEMINI_API_KEY sea correcta."
        memoria.agregar_interaccion(pregunta, error_msg, exitosa=False)
        return error_msg


def consultar_clon(id_clon, pregunta, session_id=None):
    """Orquesta la consulta decidiendo si usa el modo online u offline."""
    datos = cargar_datos()
    if id_clon not in datos["clones"]:
        print(f"\n[ERROR] El clon '{id_clon}' no existe.")
        return None

    clon = datos["clones"][id_clon]
    api_key = os.environ.get("GEMINI_API_KEY")

    if api_key:
        return consultar_clon_online(clon, pregunta, api_key, session_id)
    return consultar_clon_offline(clon, pregunta, session_id)


def obtener_historial_conversacion(id_clon, session_id=None):
    """Obtiene el historial de conversación de un clon."""
    memoria = ConversacionMemoria(id_clon, session_id)
    return memoria.historial


def limpiar_memoria_conversacion(id_clon, session_id=None):
    """Limpia la memoria de conversación de un clon."""
    memoria = ConversacionMemoria(id_clon, session_id)
    memoria.limpiar_memoria()


def obtener_estadisticas_clon(id_clon):
    """Obtiene estadísticas de uso de un clon."""
    memoria = ConversacionMemoria(id_clon)

    stats = {
        "total_interacciones": len(memoria.historial),
        "memorias_exito": len(memoria.memorias_exito),
        "temas_mas_frecuentes": [],
        "ultima_interaccion": None
    }

    if memoria.contexto.get("temas"):
        temas_ordenados = sorted(
            memoria.contexto["temas"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        stats["temas_mas_frecuentes"] = [{"tema": t, "frecuencia": f} for t, f in temas_ordenados]

    if memoria.historial:
        stats["ultima_interaccion"] = memoria.historial[-1].get("timestamp")

    return stats


def menu():
    inicializar_db()
    while True:
        print("\n" + "="*45)
        print("    SKILLTWIN MOTOR DE CLONACIÓN v2.0")
        print("="*45)
        print("1. Ver clones creados")
        print("2. Registrar / Entrenar nuevo clon")
        print("3. Consultar a un clon digital")
        print("4. Ver historial de conversación")
        print("5. Ver estadísticas de un clon")
        print("6. Limpiar memoria de conversación")
        print("7. Salir")

        opcion = input("\nSelecciona una opción (1-7): ").strip()

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
                print("\n[AVISO] Todos los campos son obligatorios.")

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
                    session_id = str(uuid.uuid4())
                    print(f"\nNueva sesión iniciada: {session_id[:8]}...")

                    while True:
                        pregunta = input(f"\nPregunta para el clon de {id_clon} (o 'salir' para terminar sesión): ").strip()
                        if pregunta.lower() in ['salir', 'exit', 'quit']:
                            break
                        if pregunta:
                            print("\n[Pensando...]")
                            respuesta = consultar_clon(id_clon, pregunta, session_id)
                            print(f"\nRespuesta:\n{respuesta}")
                else:
                    print("\n[AVISO] Seleccion invalida.")
            except ValueError:
                print("\n[AVISO] Debe ingresar un numero.")

        elif opcion == "4":
            datos = cargar_datos()
            print("\n--- VER HISTORIAL DE CONVERSACIÓN ---")
            clones_disponibles = list(datos["clones"].keys())
            for idx, cid in enumerate(clones_disponibles, 1):
                print(f"{idx}. {cid}")

            sel = input("\nSelecciona el número del clon: ").strip()
            try:
                clon_idx = int(sel) - 1
                if 0 <= clon_idx < len(clones_disponibles):
                    id_clon = clones_disponibles[clon_idx]
                    historial = obtener_historial_conversacion(id_clon)

                    if not historial:
                        print(f"\nNo hay historial de conversación para {id_clon}.")
                    else:
                        print(f"\n--- HISTORIAL DE {id_clon} ---")
                        for i, interaccion in enumerate(historial[-10:], 1):
                            print(f"\n{i}. [{interaccion['timestamp']}]")
                            print(f"   P: {interaccion['pregunta']}")
                            print(f"   R: {interaccion['respuesta'][:100]}...")
            except ValueError:
                print("\n[AVISO] Debe ingresar un numero.")

        elif opcion == "5":
            datos = cargar_datos()
            print("\n--- VER ESTADÍSTICAS DE UN CLON ---")
            clones_disponibles = list(datos["clones"].keys())
            for idx, cid in enumerate(clones_disponibles, 1):
                print(f"{idx}. {cid}")

            sel = input("\nSelecciona el número del clon: ").strip()
            try:
                clon_idx = int(sel) - 1
                if 0 <= clon_idx < len(clones_disponibles):
                    id_clon = clones_disponibles[clon_idx]
                    stats = obtener_estadisticas_clon(id_clon)

                    print(f"\n--- ESTADÍSTICAS DE {id_clon} ---")
                    print(f"Total de interacciones: {stats['total_interacciones']}")
                    print(f"Memorias de éxito: {stats['memorias_exito']}")

                    if stats['temas_mas_frecuentes']:
                        print("\nTemas más frecuentes:")
                        for tema in stats['temas_mas_frecuentes']:
                            print(f"  - {tema['tema']}: {tema['frecuencia']} veces")

                    if stats['ultima_interaccion']:
                        print(f"\nÚltima interacción: {stats['ultima_interaccion']}")
            except ValueError:
                print("\n[AVISO] Debe ingresar un numero.")

        elif opcion == "6":
            datos = cargar_datos()
            print("\n--- LIMPIAR MEMORIA DE CONVERSACIÓN ---")
            clones_disponibles = list(datos["clones"].keys())
            for idx, cid in enumerate(clones_disponibles, 1):
                print(f"{idx}. {cid}")

            sel = input("\nSelecciona el número del clon: ").strip()
            try:
                clon_idx = int(sel) - 1
                if 0 <= clon_idx < len(clones_disponibles):
                    id_clon = clones_disponibles[clon_idx]
                    limpiar_memoria_conversacion(id_clon)
                    print(f"\n✅ Memoria de conversación limpiada para {id_clon}.")
            except ValueError:
                print("\n[AVISO] Debe ingresar un numero.")

        elif opcion == "7":
            print("\n¡Gracias por usar SkillTwin! Cerrando motor de desarrollo...")
            break
        else:
            print("\n[AVISO] Opcion no valida. Intentalo de nuevo.")


if __name__ == "__main__":
    menu()
