import os
import sys
import tempfile
import unittest
import json
from datetime import datetime, timedelta

# Forzar modo JSON para tests
os.environ["SKILLTWIN_USE_SQLITE"] = "0"

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import gestor_financiero


class GestorFinancieroTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'finanzas_test.json')
        gestor_financiero.DB_FINANZAS = self.db_path
        gestor_financiero.inicializar_finanzas()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_inicializar_finanzas_crea_archivo(self):
        self.assertTrue(os.path.exists(self.db_path))

    def test_inicializar_finanzas_estructura_correcta(self):
        datos = gestor_financiero.cargar_finanzas()
        self.assertIn('flujo_caja', datos)
        self.assertIn('cuentas_cobrar', datos)
        self.assertIn('cuentas_pagar', datos)

    def test_cargar_finanzas_datos_iniciales(self):
        datos = gestor_financiero.cargar_finanzas()
        self.assertEqual(len(datos['cuentas_cobrar']), 3)
        self.assertEqual(len(datos['cuentas_pagar']), 3)

    def test_guardar_y_cargar_finanzas(self):
        datos = gestor_financiero.cargar_finanzas()
        datos['cuentas_cobrar'].append({
            'id': 'FAC-TEST',
            'cliente': 'Cliente Test',
            'monto': 500.0,
            'vencimiento': '2026-08-01',
            'estado': 'Pendiente'
        })
        gestor_financiero.guardar_finanzas(datos)

        datos_cargados = gestor_financiero.cargar_finanzas()
        self.assertEqual(len(datos_cargados['cuentas_cobrar']), 4)

    def test_flujo_caja_tiene_meses(self):
        datos = gestor_financiero.cargar_finanzas()
        self.assertIn('2026-05', datos['flujo_caja'])
        self.assertIn('2026-06', datos['flujo_caja'])
        self.assertIn('2026-07', datos['flujo_caja'])

    def test_flujo_caja_campos_requeridos(self):
        datos = gestor_financiero.cargar_finanzas()
        for mes, valores in datos['flujo_caja'].items():
            self.assertIn('ingresos_plan', valores)
            self.assertIn('ingresos_real', valores)
            self.assertIn('egresos_plan', valores)
            self.assertIn('egresos_real', valores)

    def test_cuentas_cobrar_campos_requeridos(self):
        datos = gestor_financiero.cargar_finanzas()
        for cuenta in datos['cuentas_cobrar']:
            self.assertIn('id', cuenta)
            self.assertIn('cliente', cuenta)
            self.assertIn('monto', cuenta)
            self.assertIn('vencimiento', cuenta)
            self.assertIn('estado', cuenta)

    def test_cuentas_pagar_campos_requeridos(self):
        datos = gestor_financiero.cargar_finanzas()
        for cuenta in datos['cuentas_pagar']:
            self.assertIn('id', cuenta)
            self.assertIn('proveedor', cuenta)
            self.assertIn('monto', cuenta)
            self.assertIn('vencimiento', cuenta)
            self.assertIn('estado', cuenta)

    def test_cuentas_cobrar_tiene_estados(self):
        datos = gestor_financiero.cargar_finanzas()
        estados = [c['estado'] for c in datos['cuentas_cobrar']]
        self.assertIn('Pendiente', estados)
        self.assertIn('Cobrado', estados)

    def test_cuentas_pagar_tiene_estados(self):
        datos = gestor_financiero.cargar_finanzas()
        estados = [p['estado'] for p in datos['cuentas_pagar']]
        self.assertIn('Pendiente', estados)
        self.assertIn('Pagado', estados)


if __name__ == '__main__':
    unittest.main()
