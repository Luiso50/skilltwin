import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import orquestador, gestor_ordenes, gestor_pagos, database  # noqa: E402


class OrquestadorTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.previous_db_path = database.DB_PATH
        database.DB_PATH = os.path.join(self.tmpdir.name, "test.db")
        database.init_database()

    def tearDown(self):
        database.DB_PATH = self.previous_db_path
        self.tmpdir.cleanup()

    def test_orquestador_creation(self):
        """Test that OrquestadorAutonomo can be created."""
        orq = orquestador.OrquestadorAutonomo()
        self.assertTrue(orq.activo)
        self.assertEqual(orq.intervalo_chequeo, 5)
        self.assertIsNone(orq.thread)

    def test_orquestador_start_stop(self):
        """Test that the orchestrator can be started and stopped."""
        orq = orquestador.OrquestadorAutonomo()
        orq.intervalo_chequeo = 0.1  # Fast for testing
        orq.iniciar()
        self.assertIsNotNone(orq.thread)
        self.assertTrue(orq.thread.is_alive())
        orq.detener()
        self.assertFalse(orq.activo)

    @patch('dep_operaciones.orquestador._broadcast_event')
    def test_procesar_orden_not_found(self, mock_broadcast):
        """Test processing an order that doesn't exist."""
        orq = orquestador.OrquestadorAutonomo()
        # Should not raise, just return silently
        orq._procesar_orden("nonexistent_order")

    @patch('dep_operaciones.orquestador._broadcast_event')
    @patch('dep_operaciones.orquestador.gestor_ordenes')
    def test_procesar_etapa_legal_error(self, mock_ordenes, mock_broadcast):
        """Test that legal stage handles errors gracefully."""
        orq = orquestador.OrquestadorAutonomo()
        orden = {
            "id": "test_order",
            "clon_id": "test_clon",
            "cliente_email": "test@example.com",
            "cantidad_horas": 10,
            "etapas": {}
        }
        mock_ordenes.obtener_orden.return_value = orden
        mock_ordenes.actualizar_etapa_orden.side_effect = None

        with patch('dep_operaciones.orquestador.motor_clonacion') as mock_motor:
            mock_motor.cargar_datos.side_effect = Exception("Test error")
            orq._procesar_etapa_legal("test_order", orden)

        mock_ordenes.actualizar_etapa_orden.assert_called()
        call_args = mock_ordenes.actualizar_etapa_orden.call_args
        self.assertEqual(call_args[0][1], "legal")
        self.assertEqual(call_args[0][2], "error")

    @patch('dep_operaciones.orquestador._broadcast_event')
    @patch('dep_operaciones.orquestador.gestor_ordenes')
    def test_procesar_etapa_desarrollo_error(self, mock_ordenes, mock_broadcast):
        """Test that development stage handles errors gracefully."""
        orq = orquestador.OrquestadorAutonomo()
        orden = {
            "id": "test_order",
            "clon_id": "nonexistent_clon",
            "cliente_email": "test@example.com",
            "etapas": {}
        }
        mock_ordenes.actualizar_etapa_orden.side_effect = None

        with patch('dep_operaciones.orquestador.motor_clonacion') as mock_motor:
            mock_motor.cargar_datos.return_value = {"clones": {}}
            orq._procesar_etapa_desarrollo("test_order", orden)

        mock_ordenes.actualizar_etapa_orden.assert_called()
        call_args = mock_ordenes.actualizar_etapa_orden.call_args
        self.assertEqual(call_args[0][1], "desarrollo")
        self.assertEqual(call_args[0][2], "error")

    @patch('dep_operaciones.orquestador._broadcast_event')
    @patch('dep_operaciones.orquestador.gestor_ordenes')
    @patch('dep_operaciones.orquestador.gestor_pagos')
    def test_procesar_etapa_operaciones(self, mock_pagos, mock_ordenes, mock_broadcast):
        """Test that operations stage calculates pricing correctly."""
        orq = orquestador.OrquestadorAutonomo()
        orden = {
            "id": "test_order",
            "clon_id": "test_clon",
            "cliente_email": "test@example.com",
            "cantidad_horas": 10,
            "descripcion_proyecto": "Test project",
            "etapas": {}
        }

        mock_ordenes.cargar_ordenes.return_value = {"ordenes": {"test_order": orden}}
        mock_ordenes.actualizar_etapa_orden.side_effect = None
        mock_ordenes.actualizar_pago_orden.side_effect = None
        mock_pagos.crear_factura.return_value = ("fact_001", {})

        # Mock settings file
        settings_path = os.path.join(os.path.dirname(__file__), '..', 'cerebro', 'server_settings.json')
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', unittest.mock.mock_open(read_data='{"commission": 15.0, "tariff_per_hour": 50.0}')):
                orq._procesar_etapa_operaciones("test_order", orden)

        mock_pagos.crear_factura.assert_called_once()
        call_args = mock_pagos.crear_factura.call_args
        # monto_total = 10 * 50 * 1.15 = 575.0
        self.assertAlmostEqual(call_args[0][2], 575.0, places=2)

    @patch('dep_operaciones.orquestador._broadcast_event')
    @patch('dep_operaciones.orquestador.gestor_ordenes')
    def test_procesar_etapa_entrega(self, mock_ordenes, mock_broadcast):
        """Test that delivery stage completes successfully."""
        orq = orquestador.OrquestadorAutonomo()
        orden = {
            "id": "test_order",
            "clon_id": "test_clon",
            "cliente_email": "test@example.com",
            "etapas": {}
        }
        mock_ordenes.actualizar_etapa_orden.side_effect = None

        with patch('dep_operaciones.orquestador.time.sleep'):
            orq._procesar_etapa_entrega("test_order", orden)

        mock_ordenes.actualizar_etapa_orden.assert_called()
        call_args = mock_ordenes.actualizar_etapa_orden.call_args
        self.assertEqual(call_args[0][1], "entrega")
        self.assertEqual(call_args[0][2], "completada")

    def test_broadcast_event_import_error(self):
        """Test that broadcast_event handles import errors gracefully."""
        with patch.dict('sys.modules', {'cerebro.server': None}):
            # Should not raise
            orquestador._broadcast_event("test", {"data": "test"})


if __name__ == '__main__':
    unittest.main()
