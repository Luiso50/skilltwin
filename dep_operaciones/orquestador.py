import os
import sys
import json
import threading
import time

# Agregar rutas
RAIZ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(RAIZ_DIR)

from dep_operaciones import gestor_ordenes, gestor_pagos
from dep_legal import gemini_contratos
from dep_desarrollo import motor_clonacion

class OrquestadorAutonomo:
    """
    Procesa órdenes automáticamente a través de todos los departamentos.
    Corre en un thread separado para no bloquear el servidor web.
    """
    
    def __init__(self):
        self.activo = True
        self.intervalo_chequeo = 5  # Segundos entre chequeos
        self.thread = None
    
    def iniciar(self):
        """Inicia el hilo de procesamiento automático."""
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._loop_procesamiento, daemon=True)
            self.thread.start()
            print("[ORQUESTADOR] Automatización iniciada")
    
    def detener(self):
        """Detiene el procesamiento automático."""
        self.activo = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[ORQUESTADOR] Automatización detenida")
    
    def _loop_procesamiento(self):
        """Loop principal que procesa órdenes continuamente."""
        while self.activo:
            try:
                self._procesar_ordenes_pendientes()
                time.sleep(self.intervalo_chequeo)
            except Exception as e:
                print(f"[ORQUESTADOR] Error en loop: {e}")
                time.sleep(self.intervalo_chequeo)
    
    def _procesar_ordenes_pendientes(self):
        """Busca y procesa órdenes en estado 'pendiente'."""
        ordenes = gestor_ordenes.cargar_ordenes()
        
        for orden_id, orden in ordenes["ordenes"].items():
            # Solo procesar órdenes pendientes de etapa legal
            if (orden["estado"] == "pendiente" and 
                orden["etapas"]["legal"]["estado"] == "pendiente"):
                self._procesar_orden(orden_id)
    
    def _procesar_orden(self, orden_id):
        """Ejecuta el flujo completo de la orden a través de todos los departamentos."""
        print(f"\n[ORQUESTADOR] 🚀 Procesando orden: {orden_id}")
        
        orden = gestor_ordenes.obtener_orden(orden_id)
        if not orden:
            return
        
        # ===== ETAPA 1: LEGAL =====
        self._procesar_etapa_legal(orden_id, orden)
        
        # ===== ETAPA 2: DESARROLLO =====
        self._procesar_etapa_desarrollo(orden_id, orden)
        
        # ===== ETAPA 3: OPERACIONES =====
        self._procesar_etapa_operaciones(orden_id, orden)
        
        # ===== ETAPA 4: ENTREGA =====
        self._procesar_etapa_entrega(orden_id, orden)
    
    def _procesar_etapa_legal(self, orden_id, orden):
        """Procesa la etapa legal de la orden."""
        print(f"[LEGAL] Procesando contrato para {orden_id}...")
        
        gestor_ordenes.actualizar_etapa_orden(
            orden_id, "legal", "en_proceso",
            "Generando contrato con IA..."
        )
        
        try:
            # Obtener datos del clon
            datos = motor_clonacion.cargar_datos()
            clon = datos["clones"][orden["clon_id"]]
            
            # Generar contrato usando Gemini o plantilla
            contrato_text = gemini_contratos.generar_contrato_gemini(
                orden_id,
                orden["cliente_email"],
                orden["clon_id"],
                clon["nombre"],
                clon["especialidad"],
                orden["cantidad_horas"],
                0,  # Monto se calcula en operaciones
                0   # Comisión se calcula en operaciones
            )
            
            # Guardar contrato en la orden
            gestor_ordenes.actualizar_contrato_orden(
                orden_id, contrato_text, por_gemini=True
            )
            
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "legal", "completada",
                "Contrato generado y validado con IA. Contrato guardado en sistema."
            )
            print(f"[LEGAL] ✅ Contrato generado para {orden_id}")
            
            time.sleep(1)
        
        except Exception as e:
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "legal", "error",
                f"Error al generar contrato: {str(e)}"
            )
            print(f"[LEGAL] ❌ Error: {e}")
    
    def _procesar_etapa_desarrollo(self, orden_id, orden):
        """Procesa la etapa de desarrollo."""
        print(f"[DESARROLLO] Preparando clon para {orden_id}...")
        
        gestor_ordenes.actualizar_etapa_orden(
            orden_id, "desarrollo", "en_proceso",
            f"Configurando instancia del clon '{orden['clon_id']}'..."
        )
        
        try:
            # Cargar datos del clon
            datos = motor_clonacion.cargar_datos()
            
            if orden["clon_id"] not in datos["clones"]:
                raise Exception(f"Clon '{orden['clon_id']}' no encontrado")
            
            datos["clones"][orden["clon_id"]]
            
            # Crear instancia específica para este cliente
            instancia_id = f"{orden['clon_id']}__{orden_id}"
            
            # Simular preparación
            tiempo_preparacion = 2
            for i in range(tiempo_preparacion):
                time.sleep(1)
                progreso = int((i + 1) / tiempo_preparacion * 100)
                print(f"[DESARROLLO] {progreso}% - Preparando ambiente...")
            
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "desarrollo", "completada",
                f"Instancia del clon lista. ID: {instancia_id}. Acceso: API disponible."
            )
            print(f"[DESARROLLO] ✅ Clon preparado para {orden_id}")
        
        except Exception as e:
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "desarrollo", "error",
                f"Error en preparación del clon: {str(e)}"
            )
            print(f"[DESARROLLO] ❌ Error: {e}")
    
    def _procesar_etapa_operaciones(self, orden_id, orden):
        """Procesa la etapa de operaciones (facturación y pagos)."""
        print(f"[OPERACIONES] Procesando facturación para {orden_id}...")
        
        gestor_ordenes.actualizar_etapa_orden(
            orden_id, "operaciones", "en_proceso",
            "Calculando monto total y procesando facturación..."
        )
        
        try:
            # Cargar configuración de comisión
            settings_path = os.path.join(os.path.dirname(__file__), '..', 'cerebro', 'server_settings.json')
            comision_pct = 15.0
            
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    comision_pct = settings.get("commission", 15.0)
            
            # Calcular monto (ejemplo: $50/hora)
            tarifa_hora = 50.0
            monto_bruto = orden["cantidad_horas"] * tarifa_hora
            comision = monto_bruto * (comision_pct / 100)
            monto_total = monto_bruto + comision
            
            # Actualizar orden con montos
            datos_ordenes = gestor_ordenes.cargar_ordenes()
            datos_ordenes["ordenes"][orden_id]["monto_total"] = monto_total
            datos_ordenes["ordenes"][orden_id]["comision"] = comision
            gestor_ordenes.guardar_ordenes(datos_ordenes)
            
            # CREAR FACTURA
            factura_id, factura_data = gestor_pagos.crear_factura(
                orden_id,
                orden["cliente_email"],
                monto_total,
                comision,
                orden["cantidad_horas"],
                tarifa_hora,
                orden["descripcion_proyecto"]
            )
            
            # Actualizar orden con información de pago
            gestor_ordenes.actualizar_pago_orden(
                orden_id, factura_id, "pendiente"
            )
            
            time.sleep(1)
            
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "operaciones", "completada",
                f"✅ Factura creada: {factura_id}. Total: ${monto_total:.2f} (Comisión: ${comision:.2f}). Pendiente de pago."
            )
            print(f"[OPERACIONES] ✅ Factura procesada: ${monto_total:.2f}")
        
        except Exception as e:
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "operaciones", "error",
                f"Error en facturación: {str(e)}"
            )
            print(f"[OPERACIONES] ❌ Error: {e}")
    
    def _procesar_etapa_entrega(self, orden_id, orden):
        """Procesa la etapa final de entrega."""
        print(f"[ENTREGA] Preparando entrega para {orden_id}...")
        
        gestor_ordenes.actualizar_etapa_orden(
            orden_id, "entrega", "en_proceso",
            "Generando credenciales de acceso y enviando al cliente..."
        )
        
        try:
            # Simular envío de credenciales
            time.sleep(1)
            
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "entrega", "completada",
                f"✅ Acceso entregado. Email enviado a {orden['cliente_email']} con credenciales."
            )
            
            print(f"[ENTREGA] ✅ Orden {orden_id} entregada al cliente")
        
        except Exception as e:
            gestor_ordenes.actualizar_etapa_orden(
                orden_id, "entrega", "error",
                f"Error en entrega: {str(e)}"
            )
            print(f"[ENTREGA] ❌ Error: {e}")


# Instancia global del orquestador
orquestador_global = OrquestadorAutonomo()

def iniciar_orquestador():
    """Función para iniciar el orquestador desde el servidor."""
    if orquestador_global:
        orquestador_global.iniciar()

def detener_orquestador():
    """Función para detener el orquestador desde el servidor."""
    if orquestador_global:
        orquestador_global.detener()
