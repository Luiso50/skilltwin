import os
import sys
import tempfile
import unittest
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'test.db')
        database.DB_PATH = self.db_path
        database.init_database()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_init_database_creates_file(self):
        self.assertTrue(os.path.exists(self.db_path))

    def test_clones_crud(self):
        # Create
        database.guardar_clone('test_clon', 'Test User', 'Testing', 'Test knowledge')
        
        # Read
        clon = database.obtener_clone('test_clon')
        self.assertIsNotNone(clon)
        self.assertEqual(clon['nombre'], 'Test User')
        self.assertEqual(clon['especialidad'], 'Testing')
        
        # Read all
        clones = database.cargar_clones()
        self.assertIn('test_clon', clones)
        self.assertEqual(len(clones), 1)

    def test_clones_duplicados(self):
        database.guardar_clone('test_clon', 'Test User', 'Testing', 'Knowledge 1')
        database.guardar_clone('test_clon', 'Test User 2', 'Testing 2', 'Knowledge 2')
        
        clones = database.cargar_clones()
        self.assertEqual(len(clones), 1)
        self.assertEqual(clones['test_clon']['conocimiento'], 'Knowledge 2')

    def test_flujo_caja_crud(self):
        database.guardar_flujo_caja('2026-07', 3500.0, 1200.0, 1200.0, 950.0)
        
        flujo = database.cargar_flujo_caja()
        self.assertIn('2026-07', flujo)
        self.assertEqual(flujo['2026-07']['ingresos_plan'], 3500.0)
        self.assertEqual(flujo['2026-07']['ingresos_real'], 1200.0)

    def test_cuentas_cobrar_crud(self):
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cuentas_cobrar (id, cliente, monto, vencimiento, estado)
                VALUES ('FAC-001', 'Test Client', 500.0, '2026-08-01', 'Pendiente')
            """)
        
        cuentas = database.cargar_cuentas_cobrar()
        self.assertEqual(len(cuentas), 1)
        self.assertEqual(cuentas[0]['cliente'], 'Test Client')
        self.assertEqual(cuentas[0]['monto'], 500.0)

    def test_cuentas_pagar_crud(self):
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cuentas_pagar (id, proveedor, monto, vencimiento, estado)
                VALUES ('PROV-001', 'Test Provider', 300.0, '2026-08-01', 'Pendiente')
            """)
        
        cuentas = database.cargar_cuentas_pagar()
        self.assertEqual(len(cuentas), 1)
        self.assertEqual(cuentas[0]['proveedor'], 'Test Provider')

    def test_ordenes_crud(self):
        orden = {
            'id': 'ORD-001',
            'cliente_email': 'test@example.com',
            'clon_id': 'test_clon',
            'cantidad_horas': 10,
            'descripcion_proyecto': 'Test project',
            'requiere_contrato': True,
            'fecha_creacion': '2026-07-19T10:00:00',
            'estado': 'pendiente',
            'etapas': {'legal': {'estado': 'pendiente'}},
            'notificaciones': [],
            'monto_total': 500.0,
            'comision': 75.0,
            'pago': {},
            'rating': {},
            'contrato': {},
            'archivos_entregables': []
        }
        
        database.guardar_orden(orden)
        
        loaded = database.obtener_orden('ORD-001')
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['cliente_email'], 'test@example.com')
        self.assertEqual(loaded['monto_total'], 500.0)
        self.assertIsInstance(loaded['etapas'], dict)

    def test_ordenes_list(self):
        for i in range(3):
            database.guardar_orden({
                'id': f'ORD-{i:03d}',
                'cliente_email': f'test{i}@example.com',
                'clon_id': 'test_clon',
                'cantidad_horas': 10,
                'fecha_creacion': '2026-07-19T10:00:00',
                'estado': 'pendiente'
            })
        
        ordenes = database.cargar_ordenes()
        self.assertEqual(len(ordenes), 3)

    def test_facturas_crud(self):
        # First create the order
        database.guardar_orden({
            'id': 'ORD-001',
            'cliente_email': 'test@example.com',
            'clon_id': 'test_clon',
            'cantidad_horas': 10,
            'fecha_creacion': '2026-07-19T10:00:00',
            'estado': 'pendiente'
        })
        
        factura = {
            'id': 'FAC-001',
            'orden_id': 'ORD-001',
            'cliente_email': 'test@example.com',
            'monto_total': 500.0,
            'comision': 75.0,
            'monto_experto': 425.0,
            'estado': 'pendiente',
            'fecha_creacion': '2026-07-19T10:00:00'
        }
        
        database.guardar_factura(factura)
        
        loaded = database.obtener_factura('FAC-001')
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['monto_total'], 500.0)
        self.assertEqual(loaded['estado'], 'pendiente')

    def test_facturas_list(self):
        for i in range(3):
            database.guardar_factura({
                'id': f'FAC-{i:03d}',
                'cliente_email': f'test{i}@example.com',
                'monto_total': 100.0 * (i + 1),
                'estado': 'pendiente',
                'fecha_creacion': '2026-07-19T10:00:00'
            })
        
        facturas = database.cargar_facturas()
        self.assertEqual(len(facturas), 3)

    def test_contactos_crud(self):
        contacto_id = database.guardar_contacto(
            'Test User', 'test@example.com', '+1234567890',
            'Test Corp', 'Demo', 'Quiero una demo'
        )
        
        contactos = database.cargar_contactos()
        self.assertEqual(len(contactos), 1)
        self.assertEqual(contactos[0]['nombre'], 'Test User')
        self.assertEqual(contactos[0]['email'], 'test@example.com')

    def test_migrar_json_a_sqlite(self):
        # Create JSON files in the expected locations
        clones_data = {
            "clones": {
                "migrated_clon": {
                    "nombre": "Migrated User",
                    "especialidad": "Migration",
                    "conocimiento": "Migrated knowledge",
                    "fecha_creacion": "2026-07-19"
                }
            }
        }
        
        # Write to the actual clones location
        clones_path = os.path.join(ROOT_DIR, "dep_desarrollo", "clones_db.json")
        backup_path = clones_path + ".backup"
        
        try:
            # Backup original
            if os.path.exists(clones_path):
                with open(clones_path, "r", encoding="utf-8") as f:
                    original = f.read()
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(original)
            
            # Write test data
            with open(clones_path, "w", encoding="utf-8") as f:
                json.dump(clones_data, f, ensure_ascii=False)
            
            # Run migration
            database.migrar_json_a_sqlite()
            
            # Verify
            clones = database.cargar_clones()
            self.assertIn('migrated_clon', clones)
            self.assertEqual(clones['migrated_clon']['nombre'], 'Migrated User')
        finally:
            # Restore original
            if os.path.exists(backup_path):
                with open(backup_path, "r", encoding="utf-8") as f:
                    original = f.read()
                with open(clones_path, "w", encoding="utf-8") as f:
                    f.write(original)
                os.remove(backup_path)


if __name__ == '__main__':
    unittest.main()
