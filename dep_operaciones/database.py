import sqlite3
import json
import os
import threading
from datetime import datetime
from contextlib import contextmanager
from typing import Generator, Optional

DB_PATH: str = os.environ.get("SKILLTWIN_DB_PATH") or os.path.join(os.path.dirname(__file__), "skilltwin.db")
db_lock: threading.RLock = threading.RLock()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_database():
    """Inicializa todas las tablas de la base de datos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabla de clones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clones (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                especialidad TEXT NOT NULL,
                conocimiento TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL
            )
        """)
        
        # Tabla de flujo de caja
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flujo_caja (
                mes TEXT PRIMARY KEY,
                ingresos_plan REAL DEFAULT 0.0,
                ingresos_real REAL DEFAULT 0.0,
                egresos_plan REAL DEFAULT 0.0,
                egresos_real REAL DEFAULT 0.0
            )
        """)
        
        # Tabla de cuentas por cobrar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cuentas_cobrar (
                id TEXT PRIMARY KEY,
                cliente TEXT NOT NULL,
                monto REAL NOT NULL,
                vencimiento TEXT NOT NULL,
                estado TEXT DEFAULT 'Pendiente'
            )
        """)
        
        # Tabla de cuentas por pagar
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cuentas_pagar (
                id TEXT PRIMARY KEY,
                proveedor TEXT NOT NULL,
                monto REAL NOT NULL,
                vencimiento TEXT NOT NULL,
                estado TEXT DEFAULT 'Pendiente'
            )
        """)
        
        # Tabla de órdenes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordenes (
                id TEXT PRIMARY KEY,
                cliente_email TEXT NOT NULL,
                clon_id TEXT NOT NULL,
                cantidad_horas INTEGER NOT NULL,
                descripcion_proyecto TEXT,
                requiere_contrato BOOLEAN DEFAULT 1,
                fecha_creacion TEXT NOT NULL,
                estado TEXT DEFAULT 'pendiente',
                etapas TEXT DEFAULT '{}',
                notificaciones TEXT DEFAULT '[]',
                monto_total REAL DEFAULT 0.0,
                comision REAL DEFAULT 0.0,
                pago TEXT DEFAULT '{}',
                rating TEXT DEFAULT '{}',
                contrato TEXT DEFAULT '{}',
                archivos_entregables TEXT DEFAULT '[]'
            )
        """)
        
        # Tabla de facturas/pagos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id TEXT PRIMARY KEY,
                orden_id TEXT,
                cliente_email TEXT NOT NULL,
                fecha_emision TEXT,
                fecha_vencimiento TEXT,
                monto_subtotal REAL DEFAULT 0.0,
                comision_plataforma REAL DEFAULT 0.0,
                monto_total REAL NOT NULL,
                moneda TEXT DEFAULT 'USD',
                estado TEXT DEFAULT 'pendiente',
                metodo_pago TEXT,
                metodo_pago_seleccionado TEXT,
                referencia_transaccion TEXT,
                detalles TEXT DEFAULT '{}',
                notas TEXT DEFAULT '',
                fecha_creacion TEXT NOT NULL,
                fecha_pago TEXT,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id)
            )
        """)
        
        # Tabla de transacciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transacciones (
                id TEXT PRIMARY KEY,
                factura_id TEXT,
                orden_id TEXT,
                cliente_email TEXT,
                tipo TEXT NOT NULL,
                monto REAL NOT NULL,
                moneda TEXT DEFAULT 'USD',
                metodo_pago TEXT,
                numero_referencia TEXT,
                codigo_autorizacion TEXT,
                detalles_respuesta TEXT DEFAULT '{}',
                estado TEXT DEFAULT 'completada',
                fecha TEXT NOT NULL,
                FOREIGN KEY (factura_id) REFERENCES facturas(id)
            )
        """)
        
        # Tabla de contactos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                telefono TEXT,
                empresa TEXT,
                interes TEXT,
                mensaje TEXT NOT NULL,
                fecha TEXT NOT NULL,
                estado TEXT DEFAULT 'nuevo'
            )
        """)
        
        # Tabla de usuarios (autenticación)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre TEXT NOT NULL,
                role TEXT DEFAULT 'customer',
                created_at TEXT NOT NULL
            )
        """)
        
        # Indices para consultas frecuentes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_email ON ordenes(cliente_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_estado ON ordenes(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ordenes_clon ON ordenes(clon_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_orden ON facturas(orden_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_estado ON facturas(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_cliente_email ON facturas(cliente_email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transacciones_factura ON transacciones(factura_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transacciones_estado ON transacciones(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transacciones_fecha ON transacciones(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactos_email ON contactos(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactos_estado ON contactos(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cuentas_cobrar_estado ON cuentas_cobrar(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cuentas_pagar_estado ON cuentas_pagar(estado)")


def migrar_json_a_sqlite():
    """Migra datos existentes de archivos JSON a SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Migrar clones
        clones_path = os.path.join(os.path.dirname(__file__), "..", "dep_desarrollo", "clones_db.json")
        if os.path.exists(clones_path):
            with open(clones_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for clon_id, clon_data in data.get("clones", {}).items():
                cursor.execute("""
                    INSERT OR IGNORE INTO clones (id, nombre, especialidad, conocimiento, fecha_creacion)
                    VALUES (?, ?, ?, ?, ?)
                """, (clon_id, clon_data["nombre"], clon_data["especialidad"], 
                      clon_data["conocimiento"], clon_data["fecha_creacion"]))
        
        # Migrar finanzas
        finanzas_path = os.path.join(os.path.dirname(__file__), "finanzas_db.json")
        if os.path.exists(finanzas_path):
            with open(finanzas_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for mes, valores in data.get("flujo_caja", {}).items():
                cursor.execute("""
                    INSERT OR REPLACE INTO flujo_caja (mes, ingresos_plan, ingresos_real, egresos_plan, egresos_real)
                    VALUES (?, ?, ?, ?, ?)
                """, (mes, valores["ingresos_plan"], valores["ingresos_real"],
                      valores["egresos_plan"], valores["egresos_real"]))
            
            for cuenta in data.get("cuentas_cobrar", []):
                cursor.execute("""
                    INSERT OR IGNORE INTO cuentas_cobrar (id, cliente, monto, vencimiento, estado)
                    VALUES (?, ?, ?, ?, ?)
                """, (cuenta["id"], cuenta["cliente"], cuenta["monto"],
                      cuenta["vencimiento"], cuenta["estado"]))
            
            for cuenta in data.get("cuentas_pagar", []):
                cursor.execute("""
                    INSERT OR IGNORE INTO cuentas_pagar (id, proveedor, monto, vencimiento, estado)
                    VALUES (?, ?, ?, ?, ?)
                """, (cuenta["id"], cuenta["proveedor"], cuenta["monto"],
                      cuenta["vencimiento"], cuenta["estado"]))
        
        # Migrar órdenes
        ordenes_path = os.path.join(os.path.dirname(__file__), "ordenes_db.json")
        if os.path.exists(ordenes_path):
            with open(ordenes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for orden_id, orden in data.get("ordenes", {}).items():
                cursor.execute("""
                    INSERT OR IGNORE INTO ordenes (id, cliente_email, clon_id, cantidad_horas,
                        descripcion_proyecto, requiere_contrato, fecha_creacion, estado, etapas,
                        notificaciones, monto_total, comision, pago, rating, contrato, archivos_entregables)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (orden["id"], orden["cliente_email"], orden["clon_id"],
                      orden["cantidad_horas"], orden.get("descripcion_proyecto", ""),
                      orden.get("requiere_contrato", True), orden["fecha_creacion"],
                      orden["estado"], json.dumps(orden.get("etapas", {})),
                      json.dumps(orden.get("notificaciones", [])),
                      orden.get("monto_total", 0.0), orden.get("comision", 0.0),
                      json.dumps(orden.get("pago", {})), json.dumps(orden.get("rating", {})),
                      json.dumps(orden.get("contrato", {})),
                      json.dumps(orden.get("archivos_entregables", []))))
        
        # Migrar pagos
        pagos_path = os.path.join(os.path.dirname(__file__), "pagos_db.json")
        if os.path.exists(pagos_path):
            with open(pagos_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for fac_id, factura in data.get("facturas", {}).items():
                cursor.execute("""
                    INSERT OR IGNORE INTO facturas (id, orden_id, cliente_email, fecha_emision,
                        fecha_vencimiento, monto_subtotal, comision_plataforma, monto_total,
                        moneda, estado, metodo_pago, metodo_pago_seleccionado, referencia_transaccion,
                        detalles, notas, fecha_creacion, fecha_pago)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (factura["id"], factura.get("orden_id"), factura.get("cliente_email", ""),
                      factura.get("fecha_emision"), factura.get("fecha_vencimiento"),
                      factura.get("monto_subtotal", 0.0), factura.get("comision_plataforma", factura.get("comision", 0.0)),
                      factura.get("monto_total", 0.0), factura.get("moneda", "USD"),
                      factura.get("estado", "pendiente"), factura.get("metodo_pago"),
                      factura.get("metodo_pago_seleccionado"), factura.get("referencia_transaccion"),
                      json.dumps(factura.get("detalles", {})), factura.get("notas", ""),
                      factura.get("fecha_creacion", datetime.now().isoformat()),
                      factura.get("fecha_pago")))

            for trans_id, trans in data.get("transacciones", {}).items():
                cursor.execute("""
                    INSERT OR IGNORE INTO transacciones (id, factura_id, orden_id, cliente_email,
                        tipo, monto, moneda, metodo_pago, numero_referencia, codigo_autorizacion,
                        detalles_respuesta, estado, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (trans["id"], trans.get("factura_id"), trans.get("orden_id"),
                      trans.get("cliente_email", ""), trans.get("tipo", "pago"),
                      trans["monto"], trans.get("moneda", "USD"), trans.get("metodo_pago"),
                      trans.get("numero_referencia", ""), trans.get("codigo_autorizacion", ""),
                      json.dumps(trans.get("detalles_respuesta", {})),
                      trans.get("estado", "completada"), trans.get("fecha")))
        
        # Migrar contactos
        contactos_path = os.path.join(os.path.dirname(__file__), "contactos_db.json")
        if os.path.exists(contactos_path):
            with open(contactos_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for contacto in data.get("contactos", []):
                cursor.execute("""
                    INSERT OR IGNORE INTO contactos (nombre, email, telefono, empresa, interes, mensaje, fecha, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (contacto["nombre"], contacto["email"], contacto.get("telefono", ""),
                      contacto.get("empresa", ""), contacto.get("interes", ""),
                      contacto["mensaje"], contacto["fecha"], contacto.get("estado", "nuevo")))


# Funciones de acceso a datos para clones
def cargar_clones():
    """Carga todos los clones de la base de datos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clones")
        rows = cursor.fetchall()
        return {row["id"]: dict(row) for row in rows}


def guardar_clone(clon_id, nombre, especialidad, conocimiento):
    """Guarda o actualiza un clone en la base de datos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO clones (id, nombre, especialidad, conocimiento, fecha_creacion)
            VALUES (?, ?, ?, ?, ?)
        """, (clon_id, nombre, especialidad, conocimiento, 
              datetime.now().strftime("%Y-%m-%d")))


def obtener_clone(clon_id):
    """Obtiene un clone por su ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clones WHERE id = ?", (clon_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# Funciones de acceso a datos para finanzas
def cargar_flujo_caja():
    """Carga el flujo de caja."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM flujo_caja ORDER BY mes")
        rows = cursor.fetchall()
        return {row["mes"]: dict(row) for row in rows}


def guardar_flujo_caja(mes, ingresos_plan, ingresos_real, egresos_plan, egresos_real):
    """Guarda o actualiza el flujo de caja de un mes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO flujo_caja (mes, ingresos_plan, ingresos_real, egresos_plan, egresos_real)
            VALUES (?, ?, ?, ?, ?)
        """, (mes, ingresos_plan, ingresos_real, egresos_plan, egresos_real))


def cargar_cuentas_cobrar():
    """Carga todas las cuentas por cobrar."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cuentas_cobrar")
        return [dict(row) for row in cursor.fetchall()]


def cargar_cuentas_pagar():
    """Carga todas las cuentas por pagar."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cuentas_pagar")
        return [dict(row) for row in cursor.fetchall()]


# Funciones de acceso a datos para órdenes
def cargar_ordenes():
    """Carga todas las órdenes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ordenes")
        rows = cursor.fetchall()
        result = {}
        for row in rows:
            d = dict(row)
            d["etapas"] = json.loads(d["etapas"])
            d["notificaciones"] = json.loads(d["notificaciones"])
            d["pago"] = json.loads(d["pago"])
            d["rating"] = json.loads(d["rating"])
            d["contrato"] = json.loads(d["contrato"])
            d["archivos_entregables"] = json.loads(d["archivos_entregables"])
            result[d["id"]] = d
        return result


def cargar_ordenes_pendientes():
    """Carga solo órdenes pendientes de procesamiento (optimizado para orquestador)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ordenes WHERE estado = 'pendiente'")
        rows = cursor.fetchall()
        result = {}
        for row in rows:
            d = dict(row)
            d["etapas"] = json.loads(d["etapas"])
            d["notificaciones"] = json.loads(d["notificaciones"])
            d["pago"] = json.loads(d["pago"])
            d["rating"] = json.loads(d["rating"])
            d["contrato"] = json.loads(d["contrato"])
            d["archivos_entregables"] = json.loads(d["archivos_entregables"])
            result[d["id"]] = d
        return result


def guardar_orden(orden):
    """Guarda o actualiza una orden."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO ordenes (id, cliente_email, clon_id, cantidad_horas,
                descripcion_proyecto, requiere_contrato, fecha_creacion, estado, etapas,
                notificaciones, monto_total, comision, pago, rating, contrato, archivos_entregables)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (orden["id"], orden["cliente_email"], orden["clon_id"],
              orden["cantidad_horas"], orden.get("descripcion_proyecto", ""),
              orden.get("requiere_contrato", True), orden["fecha_creacion"],
              orden["estado"], json.dumps(orden.get("etapas", {})),
              json.dumps(orden.get("notificaciones", [])),
              orden.get("monto_total", 0.0), orden.get("comision", 0.0),
              json.dumps(orden.get("pago", {})), json.dumps(orden.get("rating", {})),
              json.dumps(orden.get("contrato", {})),
              json.dumps(orden.get("archivos_entregables", []))))


def obtener_orden(orden_id):
    """Obtiene una orden por su ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["etapas"] = json.loads(d["etapas"])
            d["notificaciones"] = json.loads(d["notificaciones"])
            d["pago"] = json.loads(d["pago"])
            d["rating"] = json.loads(d["rating"])
            d["contrato"] = json.loads(d["contrato"])
            d["archivos_entregables"] = json.loads(d["archivos_entregables"])
            return d
        return None


# Funciones de acceso a datos para facturas
def cargar_facturas():
    """Carga todas las facturas."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM facturas")
        return {row["id"]: dict(row) for row in cursor.fetchall()}


def guardar_factura(factura):
    """Guarda o actualiza una factura."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO facturas (id, orden_id, cliente_email, fecha_emision,
                fecha_vencimiento, monto_subtotal, comision_plataforma, monto_total,
                moneda, estado, metodo_pago, metodo_pago_seleccionado, referencia_transaccion,
                detalles, notas, fecha_creacion, fecha_pago)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (factura["id"], factura.get("orden_id"), factura.get("cliente_email"),
              factura.get("fecha_emision"), factura.get("fecha_vencimiento"),
              factura.get("monto_subtotal", 0.0), factura.get("comision_plataforma", 0.0),
              factura["monto_total"], factura.get("moneda", "USD"), factura["estado"],
              factura.get("metodo_pago"), factura.get("metodo_pago_seleccionado"),
              factura.get("referencia_transaccion"),
              json.dumps(factura.get("detalles", {})),
              factura.get("notas", ""),
              factura.get("fecha_creacion", datetime.now().isoformat()),
              factura.get("fecha_pago")))


def obtener_factura(factura_id):
    """Obtiene una factura por su ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM facturas WHERE id = ?", (factura_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# Funciones de acceso a datos para contactos
def cargar_contactos():
    """Carga todos los contactos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contactos")
        return [dict(row) for row in cursor.fetchall()]


def guardar_contacto(nombre, email, telefono, empresa, interes, mensaje):
    """Guarda un nuevo contacto."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contactos (nombre, email, telefono, empresa, interes, mensaje, fecha, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'nuevo')
        """, (nombre, email, telefono, empresa, interes, mensaje,
              datetime.now().isoformat()))
        return cursor.lastrowid


# Funciones de acceso a datos para usuarios
def crear_usuario(email, password_hash, nombre, role="customer"):
    """Crea un nuevo usuario. Retorna el ID o None si el email ya existe."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (email, password_hash, nombre, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (email.lower().strip(), password_hash, nombre, role,
                  datetime.now().isoformat()))
            return cursor.lastrowid
        except Exception:
            return None


def obtener_usuario_por_email(email):
    """Obtiene un usuario por su email."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def obtener_usuario_por_id(user_id):
    """Obtiene un usuario por su ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
