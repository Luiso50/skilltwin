import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)


class RuntimeStorageModeTests(unittest.TestCase):
    def test_financiero_switches_to_json_when_env_changes(self):
        from dep_operaciones import gestor_financiero

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"SKILLTWIN_USE_SQLITE": "1"}, clear=False):
                import importlib
                importlib.reload(gestor_financiero)

            json_path = os.path.join(tmpdir, "finanzas.json")
            with patch.dict(os.environ, {"SKILLTWIN_USE_SQLITE": "0"}, clear=False):
                gestor_financiero.DB_FINANZAS = json_path
                gestor_financiero.inicializar_finanzas()
                datos = gestor_financiero.cargar_finanzas()

            self.assertTrue(os.path.exists(json_path))
            self.assertIn("flujo_caja", datos)
            self.assertIn("cuentas_cobrar", datos)

    def test_motor_clonacion_switches_to_json_when_env_changes(self):
        from dep_desarrollo import motor_clonacion

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"SKILLTWIN_USE_SQLITE": "1"}, clear=False):
                import importlib
                importlib.reload(motor_clonacion)

            json_path = os.path.join(tmpdir, "clones.json")
            with patch.dict(os.environ, {"SKILLTWIN_USE_SQLITE": "0"}, clear=False):
                motor_clonacion.DB_FILE = json_path
                motor_clonacion.inicializar_db()
                datos = motor_clonacion.cargar_datos()

            self.assertTrue(os.path.exists(json_path))
            self.assertIn("clones", datos)

    def test_ordenes_switches_to_json_when_env_changes(self):
        from dep_operaciones import gestor_ordenes

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"SKILLTWIN_USE_SQLITE": "1"}, clear=False):
                import importlib
                importlib.reload(gestor_ordenes)

            json_path = os.path.join(tmpdir, "ordenes.json")
            with patch.dict(os.environ, {"SKILLTWIN_USE_SQLITE": "0"}, clear=False):
                gestor_ordenes.DB_ORDENES = json_path
                gestor_ordenes.inicializar_ordenes()
                orden_id, orden = gestor_ordenes.crear_orden(
                    "cliente@example.com",
                    "clon-test",
                    4,
                    "Proyecto demo",
                    True,
                )
                loaded = gestor_ordenes.cargar_ordenes()

            self.assertTrue(os.path.exists(json_path))
            self.assertEqual(orden_id, loaded["ordenes"][orden_id]["id"])
            self.assertEqual(orden["cliente_email"], "cliente@example.com")


if __name__ == '__main__':
    unittest.main()
