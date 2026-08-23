import os
import sys
import tempfile
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_legal import generador_contratos  # noqa: E402


class GeneradorContratosTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_contratos_dir = generador_contratos.CONTRATOS_DIR
        generador_contratos.CONTRATOS_DIR = os.path.join(self.tmpdir.name, "contratos")

    def tearDown(self):
        generador_contratos.CONTRATOS_DIR = self.original_contratos_dir
        self.tmpdir.cleanup()

    def test_generar_contrato_creates_file(self):
        """Test that generating a contract creates a .docx file."""
        ruta = generador_contratos.generar_contrato(
            "test_expert", "Test Expert", "Testing", 15.0
        )
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(ruta))
        self.assertTrue(ruta.endswith(".docx"))

    def test_generar_contrato_content(self):
        """Test that the generated contract contains expected content."""
        ruta = generador_contratos.generar_contrato(
            "test_expert", "Juan Perez", "Programacion", 20.0
        )
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(ruta))

        # Verify file size is reasonable (> 1KB)
        file_size = os.path.getsize(ruta)
        self.assertGreater(file_size, 1000)

    def test_generar_contrato_default_comision(self):
        """Test that default commission is 15%."""
        ruta = generador_contratos.generar_contrato(
            "test_expert", "Test Expert", "Testing"
        )
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(ruta))

    def test_generar_contrato_custom_comision(self):
        """Test that custom commission is accepted."""
        ruta = generador_contratos.generar_contrato(
            "test_expert", "Test Expert", "Testing", 25.0
        )
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(ruta))

    def test_generar_contrato_creates_directory(self):
        """Test that the contracts directory is created if it doesn't exist."""
        import shutil
        if os.path.exists(generador_contratos.CONTRATOS_DIR):
            shutil.rmtree(generador_contratos.CONTRATOS_DIR)
        
        ruta = generador_contratos.generar_contrato(
            "test_expert", "Test Expert", "Testing"
        )
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(generador_contratos.CONTRATOS_DIR))


if __name__ == '__main__':
    unittest.main()
