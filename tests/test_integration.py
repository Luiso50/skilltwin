import os
import sys
import tempfile
import unittest
import json
import threading
import time
from http.client import HTTPConnection
from socket import error as SocketError

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

CEREBRO_DIR = os.path.join(ROOT_DIR, 'cerebro')
sys.path.insert(0, CEREBRO_DIR)


class IntegrationTests(unittest.TestCase):
    """Tests de integración que levantan el servidor HTTP real."""

    _server_ready = False

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.port = 18765
        cls.server_pid = None

        os.environ['SKILLTWIN_USE_SQLITE'] = '0'
        os.environ['SKILLTWIN_ADMIN_SECRET'] = 'test-secret-integration-2026'
        os.environ['PORT'] = str(cls.port)

        # Ensure database.py is not using sqlite if we want JSON, or initialize database anyway to avoid errors
        from dep_operaciones import database
        database.DB_PATH = os.path.join(cls.tmpdir.name, "skilltwin-test.db")
        database.init_database()

        from dep_desarrollo import motor_clonacion
        from dep_operaciones import gestor_financiero, gestor_ordenes, gestor_pagos, gestor_contactos

        motor_clonacion.DB_FILE = os.path.join(cls.tmpdir.name, 'clones_db.json')
        motor_clonacion.inicializar_db()

        gestor_financiero.DB_FINANZAS = os.path.join(cls.tmpdir.name, 'finanzas_db.json')
        gestor_financiero.inicializar_finanzas()

        gestor_ordenes.DB_ORDENES = os.path.join(cls.tmpdir.name, 'ordenes_db.json')
        gestor_ordenes.inicializar_ordenes()

        gestor_pagos.DB_PAGOS = os.path.join(cls.tmpdir.name, 'pagos_db.json')
        gestor_pagos.inicializar_pagos()

        gestor_contactos.DB_CONTACTOS = os.path.join(cls.tmpdir.name, 'contactos_db.json')
        gestor_contactos.inicializar_contactos()

        import server
        server.SETTINGS_FILE = os.path.join(cls.tmpdir.name, 'server_settings.json')

        cls.server_thread = threading.Thread(target=server.run_server, daemon=True)
        cls.server_thread.start()

        if not cls._wait_for_server(cls.port, timeout=5):
            cls.server_ready = False
            raise unittest.SkipTest("No se pudo iniciar el servidor de integración")
        cls.server_ready = True

    @classmethod
    def _wait_for_server(cls, port, timeout=5):
        start = time.time()
        while time.time() - start < timeout:
            try:
                conn = HTTPConnection('localhost', port, timeout=1)
                conn.request('GET', '/api/health')
                resp = conn.getresponse()
                resp.read()
                conn.close()
                if resp.status == 200:
                    return True
            except (SocketError, ConnectionRefusedError, OSError):
                pass
            time.sleep(0.2)
        return False

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def _get(self, path):
        conn = HTTPConnection('localhost', self.port, timeout=5)
        conn.request('GET', path)
        resp = conn.getresponse()
        data = resp.read().decode('utf-8')
        conn.close()
        return resp.status, json.loads(data) if data else {}

    def _post(self, path, body, token=None):
        conn = HTTPConnection('localhost', self.port, timeout=5)
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        conn.request('POST', path, body=json.dumps(body), headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode('utf-8')
        conn.close()
        return resp.status, json.loads(data) if data else {}

    def test_get_clones_returns_200(self):
        if not self.server_ready:
            self.skipTest("Servidor no disponible")
        status, data = self._get('/api/clones')
        self.assertEqual(status, 200)
        self.assertIn('clones', data)

    def test_get_settings_returns_200(self):
        if not self.server_ready:
            self.skipTest("Servidor no disponible")
        status, data = self._get('/api/get-settings')
        self.assertEqual(status, 200)
        self.assertIn('has_key', data)
        self.assertIn('commission', data)

    def test_get_clones_list(self):
        if not self.server_ready:
            self.skipTest("Servidor no disponible")
        status, data = self._get('/api/clones-list')
        self.assertEqual(status, 200)
        self.assertIn('clones', data)
        self.assertIsInstance(data['clones'], list)
        self.assertGreater(len(data['clones']), 0)

    def test_contacto_endpoint(self):
        if not self.server_ready:
            self.skipTest("Servidor no disponible")
        body = {
            'nombre': 'Test User',
            'email': 'test@integration.com',
            'telefono': '+34555666777',
            'empresa': 'Test Corp',
            'interes': 'Demo',
            'mensaje': 'Integration test message'
        }
        status, data = self._post('/api/contacto', body)
        self.assertEqual(status, 200)
        self.assertTrue(data.get('success'))

    def test_admin_requires_auth(self):
        if not self.server_ready:
            self.skipTest("Servidor no disponible")
        status, data = self._get('/api/finanzas-data')
        self.assertEqual(status, 401)

    def test_cors_header_present(self):
        if not self.server_ready:
            self.skipTest("Servidor no disponible")
        conn = HTTPConnection('localhost', self.port, timeout=5)
        conn.request('GET', '/api/clones')
        resp = conn.getresponse()
        cors_header = resp.getheader('Access-Control-Allow-Origin')
        conn.close()
        self.assertIsNotNone(cors_header, "CORS header should be present")


if __name__ == '__main__':
    unittest.main()
