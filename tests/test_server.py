import os
import sys
import tempfile
import unittest
import json
from http.server import HTTPServer
from unittest.mock import patch, MagicMock
import threading
import time

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

CEREBRO_DIR = os.path.join(ROOT_DIR, 'cerebro')
sys.path.insert(0, CEREBRO_DIR)


class ServerConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_path = os.path.join(self.tmpdir.name, 'server_settings_test.json')

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_cargar_ajustes_archivo_no_existe(self):
        import importlib
        import server
        server.SETTINGS_FILE = self.settings_path
        ajustes = server.cargar_ajustes()
        self.assertIn('gemini_key', ajustes)
        self.assertIn('commission', ajustes)
        self.assertIn('model', ajustes)

    def test_cargar_ajustes_archivo_existe(self):
        import importlib
        import server
        config_test = {'gemini_key': 'test_key_123', 'commission': 20.0, 'model': 'gemini-test'}
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(config_test, f)
        server.SETTINGS_FILE = self.settings_path

        ajustes = server.cargar_ajustes()
        self.assertEqual(ajustes['gemini_key'], 'test_key_123')
        self.assertEqual(ajustes['commission'], 20.0)

    def test_guardar_ajustes(self):
        import importlib
        import server
        server.SETTINGS_FILE = self.settings_path
        nuevos_ajustes = {'gemini_key': 'nueva_key', 'commission': 25.0, 'model': 'nuevo_modelo'}
        server.guardar_ajustes(nuevos_ajustes)

        with open(self.settings_path, 'r', encoding='utf-8') as f:
            guardados = json.load(f)
        self.assertEqual(guardados['gemini_key'], 'nueva_key')
        self.assertEqual(guardados['commission'], 25.0)


class ServerEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.orig_db = os.path.join(self.tmpdir.name, 'clones_db.json')
        self.finanzas_db = os.path.join(self.tmpdir.name, 'finanzas_db.json')
        self.ordenes_db = os.path.join(self.tmpdir.name, 'ordenes_db.json')
        self.pagos_db = os.path.join(self.tmpdir.name, 'pagos_db.json')
        self.contactos_db = os.path.join(self.tmpdir.name, 'contactos_db.json')

        from dep_desarrollo import motor_clonacion
        from dep_operaciones import gestor_financiero, gestor_ordenes, gestor_pagos, gestor_contactos

        motor_clonacion.DB_FILE = self.orig_db
        motor_clonacion.inicializar_db()

        gestor_financiero.DB_FINANZAS = self.finanzas_db
        gestor_financiero.inicializar_finanzas()

        gestor_ordenes.DB_ORDENES = self.ordenes_db
        gestor_ordenes.inicializar_ordenes()

        gestor_pagos.DB_PAGOS = self.pagos_db
        gestor_pagos.inicializar_pagos()

        gestor_contactos.DB_CONTACTOS = self.contactos_db
        gestor_contactos.inicializar_contactos()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_modulos_importan_correctamente(self):
        from dep_desarrollo import motor_clonacion
        from dep_operaciones import gestor_financiero, gestor_ordenes, gestor_pagos, gestor_contactos
        from dep_legal import generador_contratos

        self.assertTrue(hasattr(motor_clonacion, 'cargar_datos'))
        self.assertTrue(hasattr(gestor_financiero, 'cargar_finanzas'))
        self.assertTrue(hasattr(gestor_ordenes, 'cargar_ordenes'))
        self.assertTrue(hasattr(gestor_pagos, 'cargar_pagos'))
        self.assertTrue(hasattr(gestor_contactos, 'cargar_contactos'))
        self.assertTrue(hasattr(generador_contratos, 'generar_contrato'))

    def test_clones_api_respuesta(self):
        from dep_desarrollo import motor_clonacion
        datos = motor_clonacion.cargar_datos()
        self.assertIn('clones', datos)
        self.assertGreater(len(datos['clones']), 0)

    def test_finanzas_api_respuesta(self):
        from dep_operaciones import gestor_financiero
        datos = gestor_financiero.cargar_finanzas()
        self.assertIn('flujo_caja', datos)
        self.assertIn('cuentas_cobrar', datos)

    def test_ordenes_api_respuesta(self):
        from dep_operaciones import gestor_ordenes
        datos = gestor_ordenes.cargar_ordenes()
        self.assertIn('ordenes', datos)
        self.assertIn('contador_ordenes', datos)

    def test_pagos_api_respuesta(self):
        from dep_operaciones import gestor_pagos
        datos = gestor_pagos.cargar_pagos()
        self.assertIn('facturas', datos)
        self.assertIn('transacciones', datos)


if __name__ == '__main__':
    unittest.main()
