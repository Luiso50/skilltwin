import os
import sys
import tempfile
import unittest
import importlib

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)


class GestorPagoOrdenTests(unittest.TestCase):
    def setUp(self):
        os.environ["SKILLTWIN_USE_SQLITE"] = "0"
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'ordenes_test.json')
        self.pagos_db_path = os.path.join(self.tmpdir.name, 'pagos_test.json')

        from dep_operaciones import gestor_ordenes, gestor_pagos
        importlib.reload(gestor_ordenes)
        importlib.reload(gestor_pagos)

        gestor_ordenes.DB_ORDENES = self.db_path
        gestor_pagos.DB_PAGOS = self.pagos_db_path
        gestor_ordenes.inicializar_ordenes()
        gestor_pagos.inicializar_pagos()

        self.gestor_ordenes = gestor_ordenes
        self.gestor_pagos = gestor_pagos

        self.orden_id, _ = gestor_ordenes.crear_orden(
            cliente_email='cliente@test.com',
            clon_id='rsanchez_cobol',
            cantidad_horas=10,
            descripcion_proyecto='QA payment flow',
            requiere_contrato=True,
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_vincular_factura_no_marca_pago_como_pagado(self):
        ok = self.gestor_ordenes.actualizar_pago_orden(self.orden_id, 'FAC-TEST-001', 'pendiente')
        self.assertTrue(ok)

        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden['pago']['factura_id'], 'FAC-TEST-001')
        self.assertEqual(orden['pago']['estado_pago'], 'pendiente')
        self.assertIsNone(orden['pago']['fecha_pago'])
        self.assertIsNone(orden['pago']['metodo_pago'])

    def test_pago_real_si_marca_factura_como_pagada(self):
        self.gestor_ordenes.actualizar_pago_orden(self.orden_id, 'FAC-TEST-001', 'pendiente')
        ok = self.gestor_ordenes.actualizar_pago_orden(self.orden_id, 'FAC-TEST-001', 'tarjeta_credito')
        self.assertTrue(ok)

        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden['pago']['estado_pago'], 'pagada')
        self.assertEqual(orden['pago']['metodo_pago'], 'tarjeta_credito')
        self.assertIsNotNone(orden['pago']['fecha_pago'])

    def test_registro_stripe_paga_factura_actualiza_orden_y_es_idempotente(self):
        from cerebro.route_handlers import stripe_api

        factura_id, factura = self.gestor_pagos.crear_factura(
            self.orden_id,
            'cliente@test.com',
            175.0,
            25.0,
            10,
            15.0,
            'QA payment flow',
        )

        stripe_api.register_stripe_payment(
            factura_id, self.orden_id, 17500, 'cs_test_123'
        )
        stripe_api.register_stripe_payment(
            factura_id, self.orden_id, 17500, 'cs_test_123'
        )

        factura_pagada = self.gestor_pagos.obtener_factura(factura_id)
        orden = self.gestor_ordenes.obtener_orden(self.orden_id)
        transacciones = self.gestor_pagos.cargar_pagos()['transacciones']
        transaccion = next(iter(transacciones.values()))

        self.assertEqual(factura_pagada['estado'], 'pagada')
        self.assertEqual(
            factura_pagada['referencia_transaccion'], transaccion['id']
        )
        self.assertEqual(transaccion['numero_referencia'], 'cs_test_123')
        self.assertEqual(orden['pago']['estado_pago'], 'pagada')
        self.assertEqual(orden['pago']['metodo_pago'], 'stripe')
        self.assertEqual(len(transacciones), 1)

    def test_crear_factura_rechaza_orden_inexistente(self):
        with self.assertRaisesRegex(ValueError, "Orden no encontrada"):
            self.gestor_pagos.crear_factura(
                'ORD-DOES-NOT-EXIST',
                'cliente@test.com',
                100.0,
                10.0,
                5,
                18.0,
                'Invalid order',
            )

        self.assertEqual(self.gestor_pagos.cargar_pagos()['facturas'], {})

    def test_cargar_ordenes_normaliza_ordenes_legacy(self):
        legacy = {
            'ordenes': {
                'ORD-LEGACY': {
                    'id': 'ORD-LEGACY',
                    'cliente_email': 'legacy@test.com',
                    'clon_id': 'ana_finanzas',
                    'cantidad_horas': 3,
                    'descripcion_proyecto': 'Legacy order',
                    'requiere_contrato': True,
                    'fecha_creacion': '2026-07-01T00:00:00',
                    'estado': 'completada',
                    'etapas': {},
                    'notificaciones': [],
                    'monto_total': 172.5,
                    'comision': 22.5,
                    'pago': {
                        'factura_id': 'FAC-LEGACY',
                        'estado_pago': 'pagada',
                        'metodo_pago': 'pendiente',
                        'fecha_pago': '2026-07-01T00:00:01'
                    }
                }
            },
            'contador_ordenes': 1
        }
        self.gestor_ordenes.guardar_ordenes(legacy)

        datos = self.gestor_ordenes.cargar_ordenes()
        orden = datos['ordenes']['ORD-LEGACY']

        self.assertIn('rating', orden)
        self.assertIn('contrato', orden)
        self.assertIn('archivos_entregables', orden)
        self.assertEqual(orden['pago']['estado_pago'], 'pendiente')
        self.assertIsNone(orden['pago']['metodo_pago'])
        self.assertIsNone(orden['pago']['fecha_pago'])

    def test_reconciliar_facturas_crea_factura_faltante_para_orden_legacy(self):
        legacy = {
            'ordenes': {
                'ORD-LEGACY': {
                    'id': 'ORD-LEGACY',
                    'cliente_email': 'legacy@test.com',
                    'clon_id': 'rsanchez_cobol',
                    'cantidad_horas': 40,
                    'descripcion_proyecto': 'Legacy mainframe support',
                    'requiere_contrato': True,
                    'fecha_creacion': '2026-07-01T00:00:00',
                    'estado': 'completada',
                    'etapas': {},
                    'notificaciones': [],
                    'monto_total': 2300.0,
                    'comision': 300.0,
                    'pago': {
                        'factura_id': None,
                        'estado_pago': 'pendiente',
                        'metodo_pago': None,
                        'fecha_pago': None
                    }
                }
            },
            'contador_ordenes': 1
        }
        self.gestor_ordenes.guardar_ordenes(legacy)
        self.gestor_pagos.guardar_pagos({
            'transacciones': {},
            'facturas': {},
            'metodos_pago': ['tarjeta_credito', 'transferencia_bancaria', 'wallet_cripto'],
            'total_procesado': 0.0
        })

        cambios = self.gestor_pagos.reconciliar_facturas_con_ordenes()
        self.assertEqual(cambios, 1)

        orden = self.gestor_ordenes.obtener_orden('ORD-LEGACY')
        self.assertIsNotNone(orden['pago']['factura_id'])
        self.assertEqual(orden['pago']['estado_pago'], 'pendiente')

        pagos = self.gestor_pagos.cargar_pagos()
        self.assertEqual(len(pagos['facturas']), 1)
        factura = next(iter(pagos['facturas'].values()))
        self.assertEqual(factura['orden_id'], 'ORD-LEGACY')
        self.assertEqual(factura['monto_total'], 2300.0)


if __name__ == '__main__':
    unittest.main()
