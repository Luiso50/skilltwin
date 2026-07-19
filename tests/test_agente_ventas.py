import os
import sys
import tempfile
import unittest
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_marketing import agente_ventas_mercado


class AgenteVentasTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.report_path = os.path.join(self.tmpdir.name, 'reporte_test.json')
        agente_ventas_mercado.REPORT_FILE = self.report_path

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_analizar_datos_offline_estructura(self):
        nicho = 'programacion COBOL'
        datos_busqueda = ['Resultado 1', 'Resultado 2']
        reporte = agente_ventas_mercado.analizar_datos_offline(datos_busqueda, nicho)

        self.assertIn('analisis_oportunidad', reporte)
        self.assertIn('empresas_objetivo', reporte)
        self.assertIn('correo_ventas', reporte)

    def test_analizar_datos_offline_contiene_nicho(self):
        nicho = 'inteligencia artificial'
        reporte = agente_ventas_mercado.analizar_datos_offline([], nicho)
        self.assertIn(nicho, reporte['analisis_oportunidad'])

    def test_analizar_datos_offline_empresas_objetivo(self):
        reporte = agente_ventas_mercado.analizar_datos_offline([], 'test')
        self.assertIsInstance(reporte['empresas_objetivo'], list)
        self.assertGreater(len(reporte['empresas_objetivo']), 0)

    def test_analizar_datos_offline_correo_contenido(self):
        reporte = agente_ventas_mercado.analizar_datos_offline([], 'test')
        self.assertIn('SkillTwin', reporte['correo_ventas'])
        self.assertIn('Asunto:', reporte['correo_ventas'])

    def test_ejecutar_inteligencia_ventas_sin_api(self):
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']

        informe = agente_ventas_mercado.ejecutar_inteligencia_ventas('testing')

        self.assertIn('fecha', informe)
        self.assertIn('nicho_analizado', informe)
        self.assertIn('reporte_ventas', informe)
        self.assertEqual(informe['nicho_analizado'], 'testing')

    def test_ejecutar_inteligencia_ventas_guarda_archivo(self):
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']

        agente_ventas_mercado.ejecutar_inteligencia_ventas('test nicho')
        self.assertTrue(os.path.exists(self.report_path))

    def test_reporte_json_valido(self):
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']

        agente_ventas_mercado.ejecutar_inteligencia_ventas('validacion')

        with open(self.report_path, 'r', encoding='utf-8') as f:
            datos = json.load(f)

        self.assertIsInstance(datos, dict)
        self.assertIn('reporte_ventas', datos)


if __name__ == '__main__':
    unittest.main()
