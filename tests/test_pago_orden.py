import os
import sys
import tempfile
import unittest
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import gestor_ordenes
from dep_operaciones import gestor_pagos


class GestorPagoOrdenTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'ordenes_test.json')
        self.pagos_db_path = os.path.join(self.tmpdir.name, 'pagos_test.json')
        gestor_ordenes.DB_ORDENES = self.db_path
        gestor_pagos.DB_PAGOS = self.pagos_db_path
        gestor_ordenes.inicializar_ordenes()
        gestor_pagos.inicializar_pagos()
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
        ok = gestor_ordenes.actualizar_pago_orden(self.orden_id, 'FAC-TEST-001', 'pendiente')
        self.assertTrue(ok)

        orden = gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden['pago']['factura_id'], 'FAC-TEST-001')
        self.assertEqual(orden['pago']['estado_pago'], 'pendiente')
        self.assertIsNone(orden['pago']['fecha_pago'])
        self.assertIsNone(orden['pago']['metodo_pago'])

    def test_pago_real_si_marca_factura_como_pagada(self):
        gestor_ordenes.actualizar_pago_orden(self.orden_id, 'FAC-TEST-001', 'pendiente')
        ok = gestor_ordenes.actualizar_pago_orden(self.orden_id, 'FAC-TEST-001', 'tarjeta_credito')
        self.assertTrue(ok)

        orden = gestor_ordenes.obtener_orden(self.orden_id)
        self.assertEqual(orden['pago']['estado_pago'], 'pagada')
        self.assertEqual(orden['pago']['metodo_pago'], 'tarjeta_credito')
        self.assertIsNotNone(orden['pago']['fecha_pago'])

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
        gestor_ordenes.guardar_ordenes(legacy)

        datos = gestor_ordenes.cargar_ordenes()
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
        gestor_ordenes.guardar_ordenes(legacy)
        gestor_pagos.guardar_pagos({
            'transacciones': {},
            'facturas': {},
            'metodos_pago': ['tarjeta_credito', 'transferencia_bancaria', 'wallet_cripto'],
            'total_procesado': 0.0
        })

        cambios = gestor_pagos.reconciliar_facturas_con_ordenes()
        self.assertEqual(cambios, 1)

        orden = gestor_ordenes.obtener_orden('ORD-LEGACY')
        self.assertIsNotNone(orden['pago']['factura_id'])
        self.assertEqual(orden['pago']['estado_pago'], 'pendiente')

        pagos = gestor_pagos.cargar_pagos()
        self.assertEqual(len(pagos['facturas']), 1)
        factura = next(iter(pagos['facturas'].values()))
        self.assertEqual(factura['orden_id'], 'ORD-LEGACY')
        self.assertEqual(factura['monto_total'], 2300.0)


if __name__ == '__main__':
    unittest.main()
