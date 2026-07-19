import os
import sys
import tempfile
import unittest
import json
from unittest.mock import patch
from io import StringIO

# Forzar modo JSON para tests
os.environ["SKILLTWIN_USE_SQLITE"] = "0"

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_desarrollo import motor_clonacion


class MotorClonacionTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'clones_test.json')
        motor_clonacion.DB_FILE = self.db_path
        motor_clonacion.inicializar_db()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_inicializar_db_crea_archivo(self):
        self.assertTrue(os.path.exists(self.db_path))

    def test_inicializar_db_contiene_clones_por_defecto(self):
        datos = motor_clonacion.cargar_datos()
        self.assertIn('clones', datos)
        self.assertIn('rsanchez_cobol', datos['clones'])
        self.assertIn('ana_finanzas', datos['clones'])

    @patch('sys.stdout', new_callable=StringIO)
    def test_crear_clon_nuevo(self, mock_stdout):
        ok = motor_clonacion.crear_clon(
            id_clon='juan_seo',
            nombre='Juan Perez',
            especialidad='Experto en SEO',
            conocimiento='El SEO es la optimizacion de motores de busqueda...'
        )
        self.assertTrue(ok)

        datos = motor_clonacion.cargar_datos()
        self.assertIn('juan_seo', datos['clones'])
        self.assertEqual(datos['clones']['juan_seo']['nombre'], 'Juan Perez')
        self.assertEqual(datos['clones']['juan_seo']['especialidad'], 'Experto en SEO')

    @patch('sys.stdout', new_callable=StringIO)
    def test_crear_clon_duplicado_falla(self, mock_stdout):
        ok = motor_clonacion.crear_clon(
            id_clon='rsanchez_cobol',
            nombre='Otra persona',
            especialidad='Otra especialidad',
            conocimiento='Otro conocimiento'
        )
        self.assertFalse(ok)

    @patch('sys.stdout', new_callable=StringIO)
    def test_crear_clon_guarda_fecha_creacion(self, mock_stdout):
        motor_clonacion.crear_clon(
            id_clon='maria_legal',
            nombre='Maria Lopez',
            especialidad='Abogada',
            conocimiento='Derecho mercantil...'
        )
        datos = motor_clonacion.cargar_datos()
        self.assertIn('fecha_creacion', datos['clones']['maria_legal'])

    def test_consultar_clon_offline_respuesta(self):
        clon = motor_clonacion.cargar_datos()['clones']['rsanchez_cobol']
        respuesta = motor_clonacion.consultar_clon_offline(clon, 'que es COBOL')
        self.assertIn('MODO OFFLINE', respuesta)
        self.assertIn('COBOL', respuesta)
        self.assertIn('Roberto', respuesta)

    def test_consultar_clon_offline_sin_api_key(self):
        clon = motor_clonacion.cargar_datos()['clones']['ana_finanzas']
        respuesta = motor_clonacion.consultar_clon_offline(clon, 'dudas de ahorro')
        self.assertIn('Finanzas Personales', respuesta)
        self.assertIn('Ana', respuesta)

    @patch('sys.stdout', new_callable=StringIO)
    def test_consultar_clon_inexistente(self, mock_stdout):
        respuesta = motor_clonacion.consultar_clon('no_existe', 'pregunta')
        self.assertIsNone(respuesta)

    def test_consultar_clon_sin_api_key_modo_offline(self):
        old_key = os.environ.get('GEMINI_API_KEY')
        os.environ.pop('GEMINI_API_KEY', None)
        try:
            respuesta = motor_clonacion.consultar_clon('rsanchez_cobol', 'que es COBOL')
            self.assertIsNotNone(respuesta)
            self.assertIn('MODO OFFLINE', respuesta)
        finally:
            if old_key:
                os.environ['GEMINI_API_KEY'] = old_key

    def test_guardar_y_cargar_datos(self):
        datos_originales = motor_clonacion.cargar_datos()
        datos_originales['clones']['test_clon'] = {
            'nombre': 'Test',
            'especialidad': 'Testing',
            'conocimiento': 'Test knowledge',
            'fecha_creacion': '2026-07-19'
        }
        motor_clonacion.guardar_datos(datos_originales)

        datos_cargados = motor_clonacion.cargar_datos()
        self.assertIn('test_clon', datos_cargados['clones'])
        self.assertEqual(datos_cargados['clones']['test_clon']['nombre'], 'Test')


if __name__ == '__main__':
    unittest.main()
