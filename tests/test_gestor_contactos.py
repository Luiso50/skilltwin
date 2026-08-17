import os
import sys
import tempfile
import unittest

# Forzar modo JSON para tests
os.environ["SKILLTWIN_USE_SQLITE"] = "0"

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import gestor_contactos  # noqa: E402


class GestorContactosTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, 'contactos_test.json')
        os.environ['SKILLTWIN_CONTACTOS_DB'] = self.db_path
        gestor_contactos.DB_CONTACTOS = self.db_path
        gestor_contactos.inicializar_contactos()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_registrar_contacto_guarda_entrada(self):
        contacto = gestor_contactos.registrar_contacto(
            nombre='Luis Pérez',
            email='luis@example.com',
            telefono='+34111222333',
            empresa='SkillTwin',
            interes='Demo corporativa',
            mensaje='Quiero ver el producto en acción.'
        )

        self.assertEqual(contacto['nombre'], 'Luis Pérez')
        self.assertEqual(contacto['email'], 'luis@example.com')

        datos = gestor_contactos.cargar_contactos()
        self.assertEqual(len(datos['contactos']), 1)
        self.assertEqual(datos['contactos'][0]['empresa'], 'SkillTwin')

    def test_registrar_contacto_genera_id(self):
        contacto = gestor_contactos.registrar_contacto(
            nombre='Ana García',
            email='ana@example.com',
            telefono='',
            empresa='',
            interes='',
            mensaje='Test'
        )
        self.assertIn('id', contacto)
        self.assertIsNotNone(contacto['id'])

    def test_registrar_contacto_genera_fecha(self):
        contacto = gestor_contactos.registrar_contacto(
            nombre='Test',
            email='test@example.com',
            telefono='',
            empresa='',
            interes='',
            mensaje='Test'
        )
        self.assertIn('fecha', contacto)
        self.assertIsNotNone(contacto['fecha'])

    def test_registrar_contacto_estado_inicial(self):
        contacto = gestor_contactos.registrar_contacto(
            nombre='Test',
            email='test@example.com',
            telefono='',
            empresa='',
            interes='',
            mensaje='Test'
        )
        self.assertEqual(contacto['estado'], 'nuevo')

    def test_registrar_multiples_contactos(self):
        for i in range(3):
            gestor_contactos.registrar_contacto(
                nombre=f'Contacto {i}',
                email=f'contacto{i}@example.com',
                telefono='',
                empresa='',
                interes='',
                mensaje=f'Mensaje {i}'
            )
        datos = gestor_contactos.cargar_contactos()
        self.assertEqual(len(datos['contactos']), 3)

    def test_cargar_contactos_vacio(self):
        datos = gestor_contactos.cargar_contactos()
        self.assertIn('contactos', datos)
        self.assertEqual(len(datos['contactos']), 0)


if __name__ == '__main__':
    unittest.main()
