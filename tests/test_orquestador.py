import os
import shutil
import sys
import tempfile
import unittest

RAIZ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, RAIZ_DIR)


class OrquestadorTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test.db")
        os.environ["SKILLTWIN_DB_PATH"] = self.db_path
        os.environ["SKILLTWIN_USE_SQLITE"] = "1"

        import importlib

        from dep_operaciones import database
        database.DB_PATH = self.db_path
        importlib.reload(database)
        database.init_database()

        from dep_operaciones import gestor_ordenes, gestor_pagos
        importlib.reload(gestor_ordenes)
        importlib.reload(gestor_pagos)

        self.gestor_ordenes = gestor_ordenes
        self.gestor_pagos = gestor_pagos

        self.orden_id, self.orden_data = gestor_ordenes.crear_orden(
            "test@example.com", "rsanchez_cobol", 10, "Test project", True
        )

    def tearDown(self):
        os.environ.pop("SKILLTWIN_DB_PATH", None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_crear_orden_genera_id(self):
        self.assertTrue(self.orden_id.startswith("ORD-"))

    def test_orden_estado_inicial(self):
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden["estado"], "pendiente")
        self.assertEqual(orden["cliente_email"], "test@example.com")

    def test_orden_etapas_iniciales(self):
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden["etapas"]["legal"]["estado"], "pendiente")
        self.assertEqual(orden["etapas"]["desarrollo"]["estado"], "pendiente")

    def test_actualizar_etapa_orden(self):
        self.gestor_ordenes.actualizar_etapa_orden(
            self.orden_id, "legal", "en_proceso", "Procesando..."
        )
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden["etapas"]["legal"]["estado"], "en_proceso")

    def test_actualizar_etapa_completada(self):
        self.gestor_ordenes.actualizar_etapa_orden(
            self.orden_id, "legal", "completada", "Contrato listo"
        )
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden["etapas"]["legal"]["estado"], "completada")

    def test_crear_factura(self):
        factura_id, factura_data = self.gestor_pagos.crear_factura(
            self.orden_id, "test@example.com", 600.0, 90.0, 10, 50.0, "Test"
        )
        self.assertTrue(factura_id.startswith("FAC-"))
        self.assertEqual(factura_data["monto_total"], 600.0)
        self.assertEqual(factura_data["moneda"], "USD")

    def test_actualizar_pago_orden(self):
        self.gestor_ordenes.actualizar_pago_orden(
            self.orden_id, "FAC-TEST", "pendiente"
        )
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden["pago"]["factura_id"], "FAC-TEST")

    def test_listar_ordenes(self):
        self.gestor_ordenes.crear_orden("other@test.com", "ana_finanzas", 5, "Other")
        ordenes = self.gestor_ordenes.listar_ordenes()
        self.assertGreaterEqual(len(ordenes), 2)

    def test_listar_ordenes_por_email(self):
        ordenes = self.gestor_ordenes.listar_ordenes("test@example.com")
        self.assertEqual(len(ordenes), 1)

    def test_flujo_completo_etapas(self):
        for etapa in ["legal", "desarrollo", "operaciones", "entrega"]:
            self.gestor_ordenes.actualizar_etapa_orden(
                self.orden_id, etapa, "completada", f"{etapa} listo"
            )
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        for etapa in ["legal", "desarrollo", "operaciones", "entrega"]:
            self.assertEqual(orden["etapas"][etapa]["estado"], "completada")

    def test_error_en_etapa(self):
        self.gestor_ordenes.actualizar_etapa_orden(
            self.orden_id, "legal", "error", "Error de contrato"
        )
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden["etapas"]["legal"]["estado"], "error")


if __name__ == "__main__":
    unittest.main()
