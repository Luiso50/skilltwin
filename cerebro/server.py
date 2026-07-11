import http.server
import socketserver
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

# Añadir el directorio raíz al path para importar los módulos de los departamentos
RAIZ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(RAIZ_DIR)

from dep_desarrollo import motor_clonacion
from dep_marketing import agente_ventas_mercado
from dep_operaciones import gestor_financiero, gestor_ordenes, gestor_pagos, gestor_contactos, orquestador
from dep_legal import generador_contratos, gemini_contratos

PORT = 8000
CEREBRO_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(CEREBRO_DIR, "server_settings.json")
DEFAULT_SETTINGS = {
    "gemini_key": "",
    "commission": 15.0,
    "model": "gemini-2.5-flash"
}

def cargar_ajustes():
    if not os.path.exists(SETTINGS_FILE):
        guardar_ajustes(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
            configuracion = DEFAULT_SETTINGS.copy()
            configuracion.update(datos)
            return configuracion
    except Exception:
        guardar_ajustes(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()


def guardar_ajustes(ajustes):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(ajustes, f, indent=4, ensure_ascii=False)


# Cargar la configuración inicial al arrancar el servidor
INICIAL_SETTINGS = cargar_ajustes()
if INICIAL_SETTINGS.get("gemini_key"):
    os.environ["GEMINI_API_KEY"] = INICIAL_SETTINGS["gemini_key"]
if INICIAL_SETTINGS.get("model"):
    os.environ["GEMINI_MODEL"] = INICIAL_SETTINGS["model"]


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        exc_type, exc, _ = sys.exc_info()
        if exc_type in (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return
        super().handle_error(request, client_address)

class CerebroHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Servir archivos estáticos desde el directorio fijo /cerebro/.
        path = urllib.parse.urlparse(path).path
        path = path.lstrip('/')
        if not path:
            path = 'index.html'

        full_path = os.path.join(CEREBRO_DIR, path)
        if os.path.isdir(full_path):
            for index in ['index.html']:
                index_file = os.path.join(full_path, index)
                if os.path.exists(index_file):
                    return index_file
        return full_path

    def end_headers(self):
        # Desactivar caché para desarrollo fluido
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        if self.path == '/favicon.ico':
            try:
                logo_path = os.path.join(CEREBRO_DIR, 'logo-mark.svg')
                with open(logo_path, 'rb') as favicon_file:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/svg+xml')
                    self.end_headers()
                    self.wfile.write(favicon_file.read())
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return
            except Exception as e:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/clones':
            try:
                datos = motor_clonacion.cargar_datos()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(datos, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/get-settings':
            try:
                ajustes = cargar_ajustes()
                has_key = bool(ajustes.get("gemini_key")) or ("GEMINI_API_KEY" in os.environ and bool(os.environ["GEMINI_API_KEY"]))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "has_key": has_key,
                    "commission": ajustes.get("commission", 15.0),
                    "model": ajustes.get("model", "gemini-2.5-flash")
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/finanzas-data':
            try:
                datos = gestor_financiero.cargar_finanzas()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(datos, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/clones-list':
            try:
                datos = motor_clonacion.cargar_datos()
                clones_lista = []
                for clon_id, clon_data in datos["clones"].items():
                    clones_lista.append({
                        "id": clon_id,
                        "nombre": clon_data.get("nombre", ""),
                        "especialidad": clon_data.get("especialidad", "")
                    })
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"clones": clones_lista}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path.startswith('/api/ordenes'):
            try:
                # GET /api/ordenes?email=cliente@email.com
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                cliente_email = params.get('email', [None])[0]
                
                ordenes = gestor_ordenes.listar_ordenes(cliente_email)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"ordenes": ordenes}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path.startswith('/api/notificaciones'):
            try:
                # GET /api/notificaciones?email=cliente@email.com
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                cliente_email = params.get('email', [None])[0]
                
                if cliente_email:
                    notificaciones = gestor_ordenes.obtener_notificaciones_no_leidas(cliente_email)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({"notificaciones": notificaciones}, ensure_ascii=False).encode('utf-8'))
                else:
                    raise Exception("Email de cliente requerido")
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path.startswith('/api/facturas'):
            try:
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                cliente_email = params.get('email', [None])[0]
                
                facturas = gestor_pagos.listar_facturas(cliente_email)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"facturas": facturas}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path.startswith('/api/admin-dashboard'):
            try:
                stats_pagos = gestor_pagos.obtener_estadisticas_pagos()
                stats_ordenes = {
                    "total_ordenes": len(gestor_ordenes.cargar_ordenes()["ordenes"]),
                    "ordenes_completadas": len([o for o in gestor_ordenes.cargar_ordenes()["ordenes"].values() if o["estado"] == "completada"])
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "pagos": stats_pagos,
                    "ordenes": stats_ordenes
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/command':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                comando = data.get("command", "").strip()
                respuesta = self.procesar_comando(comando)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(respuesta, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/crear-orden':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                cliente_email = data.get("cliente_email", "").strip()
                clon_id = data.get("clon_id", "").strip()
                cantidad_horas = data.get("cantidad_horas", 0)
                descripcion_proyecto = data.get("descripcion_proyecto", "").strip()
                requiere_contrato = data.get("requiere_contrato", True)
                
                if not cliente_email or not clon_id or cantidad_horas <= 0:
                    raise ValueError("Datos incompletos o inválidos")
                
                orden_id, orden_data = gestor_ordenes.crear_orden(
                    cliente_email, clon_id, cantidad_horas, 
                    descripcion_proyecto, requiere_contrato
                )
                
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "orden_id": orden_id,
                    "mensaje": f"Orden creada exitosamente. Se procesará automáticamente.",
                    "orden": orden_data
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path.startswith('/api/marcar-leida'):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                orden_id = data.get("orden_id", "").strip()
                indice = data.get("indice", 0)
                
                exito = gestor_ordenes.marcar_notificacion_leida(orden_id, indice)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": exito,
                    "mensaje": "Notificación marcada como leída"
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/chat-clon':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                id_clon = data.get("id_clon", "").strip()
                pregunta = data.get("pregunta", "").strip()
                
                respuesta_clon = motor_clonacion.consultar_clon(id_clon, pregunta)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"respuesta": respuesta_clon}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/procesar-pago':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                factura_id = data.get("factura_id", "").strip()
                metodo_pago = data.get("metodo_pago", "tarjeta_credito").strip()
                
                exito, resultado = gestor_pagos.procesar_pago(factura_id, metodo_pago)
                
                if exito:
                    # Obtener la factura para actualizarla en la orden
                    factura = gestor_pagos.obtener_factura(factura_id)
                    if factura:
                        gestor_ordenes.actualizar_pago_orden(
                            factura["orden_id"], factura_id, metodo_pago
                        )
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": True,
                        "mensaje": "Pago procesado exitosamente",
                        "resultado": resultado
                    }, ensure_ascii=False).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": resultado}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/agregar-rating':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                orden_id = data.get("orden_id", "").strip()
                puntuacion = data.get("puntuacion", 0)
                resena = data.get("resena", "").strip()
                
                exito, mensaje = gestor_ordenes.agregar_rating_orden(orden_id, puntuacion, resena)
                
                if exito:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": True,
                        "mensaje": mensaje
                    }, ensure_ascii=False).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": mensaje}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/contacto':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                nombre = data.get("nombre", "").strip()
                email = data.get("email", "").strip()
                telefono = data.get("telefono", "").strip()
                empresa = data.get("empresa", "").strip()
                interes = data.get("interes", "").strip()
                mensaje = data.get("mensaje", "").strip()

                if not nombre or not email or not mensaje:
                    raise ValueError("Nombre, email y mensaje son obligatorios")

                contacto = gestor_contactos.registrar_contacto(
                    nombre, email, telefono, empresa, interes, mensaje
                )

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "message": "Solicitud recibida correctamente. Te responderemos en breve.",
                    "contacto": contacto
                }, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/api/settings':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                api_key = data.get("gemini_key", "").strip()
                commission = data.get("commission")
                model = data.get("model", "gemini-2.5-flash").strip()

                ajustes = cargar_ajustes()
                mensaje_parts = []

                if api_key:
                    ajustes["gemini_key"] = api_key
                    os.environ["GEMINI_API_KEY"] = api_key
                    mensaje_parts.append("GEMINI_API_KEY guardada exitosamente.")
                elif "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"]:
                    mensaje_parts.append("GEMINI_API_KEY permanece sin cambios.")

                if commission is not None:
                    try:
                        ajustes["commission"] = float(commission)
                        mensaje_parts.append(f"Comisión ajustada a {commission}%.")
                    except ValueError:
                        mensaje_parts.append("Comisión inválida entregada; se mantuvo el valor anterior.")

                if model:
                    ajustes["model"] = model
                    os.environ["GEMINI_MODEL"] = model
                    mensaje_parts.append(f"Modelo LLM seleccionado: {model}.")

                guardar_ajustes(ajustes)
                msg = " ".join(mensaje_parts) if mensaje_parts else "Configuración procesada sin cambios."

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "message": msg}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def clasificar_intencion_ia(self, comando):
        """Utiliza Gemini para analizar la intención del usuario y normalizar el comando."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativetoolkit.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        prompt = (
            f"Eres el Cerebro Central de SkillTwin. Analiza el siguiente comando del usuario y clasifícalo en un departamento.\n\n"
            f"DEPARTAMENTOS Y COMANDOS NORMALIZADOS:\n"
            f"1. operaciones -> Comando: 'finanzas' (Cualquier consulta sobre dinero, caja, flujo, pagos).\n"
            f"2. marketing -> Comando: 'marketing [nicho]' (Cualquier búsqueda de mercado, nicho o ventas. Extrae el nicho).\n"
            f"3. legal -> Comando: 'contrato [Nombre] [ID] [Especialidad] [Comision]' (Redacción de acuerdos. Intenta extraer los datos o usa valores genéricos).\n"
            f"4. desarrollo -> Comando: 'preguntar [ID_Clon] [pregunta]' (Consultas a gemelos digitales. Extrae el ID y la pregunta).\n"
            f"5. general -> Comando: 'general' (Saludos, ayuda o temas no relacionados).\n\n"
            f"USUARIO: \"{comando}\"\n\n"
            f"Responde estrictamente en formato JSON con esta estructura:\n"
            f"{{\n"
            f"  \"intent\": \"nombre_del_departamento\",\n"
            f"  \"normalized_command\": \"comando_exacto\",\n"
            f"  \"reasoning\": \"explicacion_breve\"\n"
            f"}}"
        )

        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                json_res = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(json_res)
        except Exception as e:
            print(f"Error en clasificación IA: {e}")
            return None

    def procesar_comando(self, comando):
        # Intentar clasificación inteligente vía IA primero
        ia_decision = self.clasificar_intencion_ia(comando)
        
        if ia_decision:
            intent = ia_decision.get("intent")
            normalized_cmd = ia_decision.get("normalized_command", "")
            reasoning = ia_decision.get("reasoning", "")
            
            # Si la IA decidió que es un comando ejecutable, usamos la versión normalizada
            if intent != "general":
                # Loguear que la IA tomó la decisión
                print(f"[IA ROUTER] Intención: {intent} | Razón: {reasoning} | Comando: {normalized_cmd}")
                # Ejecutamos la lógica usando el comando normalizado por la IA
                return self.ejecutar_logica_comando(normalized_cmd, ia_tag=intent)

        # Fallback: Ruteo tradicional basado en palabras clave
        return self.ejecutar_logica_comando(comando)

    def ejecutar_logica_comando(self, comando, ia_tag=None):
        cmd_lower = comando.lower()
        
        # 1. COMANDO DE FINANZAS
        if "finanzas" in cmd_lower or "flujo" in cmd_lower or "caja" in cmd_lower:
            datos_fin = gestor_financiero.cargar_finanzas()
            
            # Formatear flujo de caja en texto
            flujo_texto = "📊 **Flujo de Caja:**\n"
            for mes, val in sorted(datos_fin["flujo_caja"].items()):
                flujo_texto += f"- **{mes}**: Ingresos: ${val['ingresos_real']} (Plan: ${val['ingresos_plan']}) | Egresos: ${val['egresos_real']} (Plan: ${val['egresos_plan']})\n"
            
            # Generar alertas
            alertas = []
            hoy = datetime.now().date()
            
            for c in datos_fin["cuentas_cobrar"]:
                if c["estado"] == "Pendiente":
                    fv = datetime.strptime(c["vencimiento"], "%Y-%m-%d").date()
                    if (fv - hoy).days < 0:
                        alertas.append(f"⚠️ **Cobro Vencido**: {c['id']} ({c['cliente']}) - ${c['monto']}")
                        
            for p in datos_fin["cuentas_pagar"]:
                if p["estado"] == "Pendiente":
                    fv = datetime.strptime(p["vencimiento"], "%Y-%m-%d").date()
                    dif = (fv - hoy).days
                    if dif < 0:
                        alertas.append(f"🚨 **Pago Vencido**: {p['id']} ({p['proveedor']}) - ${p['monto']}")
                    elif 0 <= dif <= 3:
                        alertas.append(f"⏰ **Pago Próximo ({dif} días)**: {p['id']} ({p['proveedor']}) - ${p['monto']}")

            alertas_texto = "🔔 **Alertas Financieras:**\n" + ("\n".join(alertas) if alertas else "Sin alertas pendientes.")
            
            return {
                "tag": ia_tag if ia_tag else "operaciones",
                "message": f"Accediendo a la base de datos financiera del departamento...\n\n{flujo_texto}\n{alertas_texto}",
                "console_log": "Consulta de base de datos financiera realizada exitosamente."
            }

        # 2. COMANDO DE INVESTIGACIÓN DE MERCADO (MARKETING)
        elif "marketing" in cmd_lower or "buscar" in cmd_lower or "nicho" in cmd_lower:
            nicho = "programacion COBOL"
            parts = comando.split(None, 1)
            if len(parts) > 1:
                nicho = parts[1]
            
            reporte = agente_ventas_mercado.ejecutar_inteligencia_ventas(nicho)
            rep_v = reporte["reporte_ventas"]
            
            msg = (
                f"📢 **Informe del Agente de Ventas para '{nicho}':**\n\n"
                f"🎯 **Análisis:** {rep_v['analisis_oportunidad']}\n\n"
                f"🏢 **Clientes Objetivo:** {', '.join(rep_v['empresas_objetivo'])}\n\n"
                f"📧 **Propuesta de Correo Frío:**\n```\n{rep_v['correo_ventas']}\n```"
            )
            return {
                "tag": ia_tag if ia_tag else "marketing",
                "message": msg,
                "console_log": f"Reporte de inteligencia generado para '{nicho}'"
            }

        # 3. COMANDO DE CREAR CONTRATO (LEGAL)
        elif "contrato" in cmd_lower or "legal" in cmd_lower:
            parts = comando.split()
            nombre = "Experto Genérico"
            id_exp = "experto_gen"
            especialidad = "Consultoría"
            comision = 15.0
            
            if len(parts) >= 4:
                nombre = parts[1]
                id_exp = parts[2]
                especialidad = " ".join(parts[3:5])
                if len(parts) >= 6:
                    try:
                        comision = float(parts[5])
                    except:
                        pass
            else:
                return {
                    "tag": ia_tag if ia_tag else "legal",
                    "message": "Para redactar un contrato usa el formato:\n`contrato [Nombre] [ID] [Especialidad] [Comision]`\nEjemplo: `contrato Juan jortiz Programacion_SEO 15`",
                    "console_log": "Intento de generación de contrato con parámetros insuficientes."
                }
                
            ruta = generador_contratos.generar_contrato(id_exp, nombre, especialidad, comision)
            return {
                "tag": ia_tag if ia_tag else "legal",
                "message": f"⚖️ **Contrato de Licencia Generado:**\n\n- **Licenciante:** {nombre}\n- **ID de Clon:** {id_exp}\n- **Especialidad:** {especialidad}\n- **Comisión:** {comision}%\n\n📄 Guardado en: `{ruta}`",
                "console_log": f"Contrato legal generado para {id_exp}."
            }

        # 4. COMANDO DE CONSULTAR CLON (DESARROLLO)
        elif "preguntar" in cmd_lower or "clon" in cmd_lower:
            parts = comando.split(None, 2)
            if len(parts) >= 3:
                id_clon = parts[1].strip()
                pregunta = parts[2].strip()
                
                respuesta_clon = motor_clonacion.consultar_clon(id_clon, pregunta)
                if respuesta_clon:
                    return {
                        "tag": ia_tag if ia_tag else "desarrollo",
                        "message": f"💬 **Respuesta de {id_clon}:**\n\n{respuesta_clon}",
                        "console_log": f"Consulta al clon '{id_clon}' completada."
                    }
                else:
                    return {
                        "tag": ia_tag if ia_tag else "desarrollo",
                        "message": f"❌ El clon '{id_clon}' no está registrado en la base de datos.",
                        "console_log": f"Fallo al consultar clon: '{id_clon}' no encontrado."
                    }
            else:
                datos_db = motor_clonacion.cargar_datos()
                clones = list(datos_db["clones"].keys())
                clones_str = "\n".join([f"- `{c}` ({datos_db['clones'][c]['especialidad']})" for c in clones])
                return {
                    "tag": ia_tag if ia_tag else "desarrollo",
                    "message": f"Para consultar a un clon usa:\n`preguntar [id_clon] [tu pregunta]`\n\n**Clones registrados actualmente:**\n{clones_str}",
                    "console_log": "Intento de consulta a clon sin parámetros."
                }

        # 5. MENSAJE POR DEFECTO
        else:
            return {
                "tag": ia_tag if ia_tag else "cerebro",
                "message": (
                    f"Comando '{comando}' recibido por el Cerebro.\n\n"
                    f"Puedo ejecutar acciones reales en tus departamentos si escribes:\n"
                    f"1. 📊 **`finanzas`**: Muestra el flujo de caja y alertas reales del negocio.\n"
                    f"2. 📢 **`marketing [nicho]`**: Realiza un estudio de mercado web real y redacta un correo persuasivo.\n"
                    f"3. ⚖️ **`contrato [Nombre] [ID] [Especialidad] [Comisión]`**: Redacta y firma un contrato de licencia.\n"
                    f"4. 💬 **`preguntar [ID_Clon] [pregunta]`**: Lanza una consulta al motor de clonación de un experto."
                ),
                "console_log": f"Comando genérico procesado por el Cerebro Central."
            }

def run_server():
    # Inicializar bases de datos por seguridad
    motor_clonacion.inicializar_db()
    gestor_financiero.inicializar_finanzas()
    gestor_ordenes.inicializar_ordenes()
    gestor_pagos.inicializar_pagos()
    
    # Iniciar orquestador automático
    orquestador.iniciar_orquestador()
    print("[SERVIDOR] Orquestador automático iniciado")
    
    Handler = CerebroHandler
    ThreadingTCPServer.allow_reuse_address = True
    with ThreadingTCPServer(("", PORT), Handler) as httpd:
        print("\n" + "="*50)
        print(f"      SERVIDOR SKILLTWIN HABILITADO EN PUERTO {PORT}")
        print("="*50)
        print(">> Abre en tu navegador: http://localhost:8000")
        print(">> Portal de Clientes: http://localhost:8000/client-portal.html")
        print(">> Panel de Admin: http://localhost:8000/admin-dashboard.html")
        print(">> Presiona CTRL+C para apagar el servidor.")
        print("="*50)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[SERVIDOR] Deteniendo orquestador...")
            orquestador.detener_orquestador()
            print("[SERVIDOR] Servidor apagado.")
            sys.exit(0)

if __name__ == "__main__":
    run_server()
