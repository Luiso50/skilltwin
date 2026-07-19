import os
import sys
import tempfile
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_legal import generador_contratos


class GeneradorContratosTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.contratos_dir = os.path.join(self.tmpdir.name, 'contratos')
        generador_contratos.CONTRATOS_DIR = self.contratos_dir

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_generar_contrato_crea_archivo(self):
        ruta = generador_contratos.generar_contrato(
            id_experto='test_user',
            nombre='Test User',
            especialidad='Testing',
            comision=15.0
        )
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(ruta))

    def test_generar_contrato_nombre_archivo(self):
        ruta = generador_contratos.generar_contrato(
            id_experto='juan_dev',
            nombre='Juan Dev',
            especialidad='Desarrollo',
            comision=15.0
        )
        self.assertIn('contrato_juan_dev.txt', ruta)

    def test_generar_contrato_contenido_nombre(self):
        ruta = generador_contratos.generar_contrato(
            id_experto='maria_ia',
            nombre='María García',
            especialidad='Inteligencia Artificial',
            comision=15.0
        )
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        self.assertIn('María García', contenido)

    def test_generar_contrato_contenido_especialidad(self):
        ruta = generador_contratos.generar_contrato(
            id_experto='pedro_data',
            nombre='Pedro López',
            especialidad='Data Science',
            comision=15.0
        )
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        self.assertIn('Data Science', contenido)

    def test_generar_contrato_comision_personalizada(self):
        ruta = generador_contratos.generar_contrato(
            id_experto='custom_comision',
            nombre='Custom User',
            especialidad='Testing',
            comision=20.0
        )
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        self.assertIn('20.0%', contenido)
        self.assertIn('80.0%', contenido)

    def test_generar_contrato_comision_por_defecto(self):
        ruta = generador_contratos.generar_contrato(
            id_experto='default_comision',
            nombre='Default User',
            especialidad='Testing'
        )
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        self.assertIn('15.0%', contenido)

    def test_generar_contrato_crea_directorio(self):
        dir_no_existente = os.path.join(self.tmpdir.name, 'nueva_carpeta', 'contratos')
        generador_contratos.CONTRATOS_DIR = dir_no_existente
        ruta = generador_contratos.generar_contrato(
            id_experto='test_dir',
            nombre='Test Dir',
            especialidad='Testing'
        )
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(dir_no_existente))

    def test_generar_contrato_formato_fecha(self):
        ruta = generador_contratos.generar_contrato(
            id_experto='fecha_test',
            nombre='Fecha Test',
            especialidad='Testing'
        )
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()
        self.assertIn('ACUERDO DE LICENCIA', contenido)
        self.assertIn('SKILLTWIN', contenido)


if __name__ == '__main__':
    unittest.main()
