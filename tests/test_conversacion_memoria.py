import os
import shutil
import sys
import tempfile
import unittest

RAIZ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, RAIZ_DIR)


class ConversacionMemoriaTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memoria_dir = os.path.join(self.test_dir, "memories")
        os.makedirs(self.memoria_dir, exist_ok=True)
        self.session_id = "test-session-001"

        from dep_desarrollo import motor_clonacion
        self._original_memory_dir = motor_clonacion.MEMORY_DIR
        motor_clonacion.MEMORY_DIR = self.memoria_dir
        self.motor = motor_clonacion

    def tearDown(self):
        self.motor.MEMORY_DIR = self._original_memory_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_crear_memoria_nueva(self):
        memoria = self.motor.ConversacionMemoria("test_clon", self.session_id)
        self.assertEqual(len(memoria.historial), 0)

    def test_agregar_interaccion(self):
        memoria = self.motor.ConversacionMemoria("test_clon", self.session_id)
        memoria.agregar_interaccion("¿Qué es COBOL?", "COBOL es un lenguaje...")
        self.assertEqual(len(memoria.historial), 1)

    def test_memoria_exito(self):
        memoria = self.motor.ConversacionMemoria("test_clon", self.session_id)
        memoria.agregar_interaccion("P1", "R1", exitosa=True)
        memoria.agregar_interaccion("P2", "R2", exitosa=True)
        memoria.agregar_interaccion("P3", "R3", exitosa=False)
        self.assertEqual(len(memoria.memorias_exito), 2)

    def test_actualizar_contexto(self):
        memoria = self.motor.ConversacionMemoria("test_clon", self.session_id)
        memoria.agregar_interaccion("¿Qué es COBOL?", "COBOL es...")
        self.assertIn("temas", memoria.contexto)
        self.assertEqual(memoria.contexto["total_interacciones"], 1)

    def test_buscar_memorias_similares(self):
        memoria = self.motor.ConversacionMemoria("test_clon", self.session_id)
        memoria.agregar_interaccion("¿Qué es COBOL?", "COBOL es un lenguaje")
        memoria.agregar_interaccion("¿Cómo se usa Python?", "Python se usa para")
        similares = memoria.buscar_memorias_similares("¿Qué es COBOL?")
        self.assertGreater(len(similares), 0)

    def test_persistencia_en_disco(self):
        memoria1 = self.motor.ConversacionMemoria("test_clon", self.session_id)
        memoria1.agregar_interaccion("Pregunta", "Respuesta")

        memoria2 = self.motor.ConversacionMemoria("test_clon", self.session_id)
        self.assertEqual(len(memoria2.historial), 1)

    def test_limpiar_memoria(self):
        memoria = self.motor.ConversacionMemoria("test_clon", self.session_id)
        memoria.agregar_interaccion("Pregunta", "Respuesta")
        memoria.limpiar_memoria()
        self.assertEqual(len(memoria.historial), 0)

    def test_tope_50_interacciones(self):
        memoria = self.motor.ConversacionMemoria("test_clon", self.session_id)
        for i in range(55):
            memoria.agregar_interaccion(f"P{i}", f"R{i}")
        self.assertEqual(len(memoria.historial), 50)


class ConocimientoEstructuradoTests(unittest.TestCase):
    def test_parsear_conocimiento(self):
        texto = (
            "Python es un lenguaje de programación. "
            "Siempre se debe usar virtual environments. "
            "Usar pip para instalar librerías. "
            "El primer paso es instalar Python. "
            "Consejo: aprende pandas para análisis de datos."
        )
        from dep_desarrollo.motor_clonacion import ConocimientoEstructurado
        conocimiento = ConocimientoEstructurado(texto)
        self.assertGreater(len(conocimiento.categorias), 0)

    def test_conceptos_clave(self):
        texto = "Python es un lenguaje. Python se usa para datos. Python es popular."
        from dep_desarrollo.motor_clonacion import ConocimientoEstructurado
        conocimiento = ConocimientoEstructurado(texto)
        self.assertGreater(len(conocimiento.conceptos_clave), 0)

    def test_buscar_informacion_relevante(self):
        texto = (
            "Python es un lenguaje de programación. "
            "SQL es para bases de datos. "
            "Docker es para containers."
        )
        from dep_desarrollo.motor_clonacion import ConocimientoEstructurado
        conocimiento = ConocimientoEstructurado(texto)
        resultados = conocimiento.buscar_informacion_relevante("¿Qué es Python?")
        self.assertGreater(len(resultados), 0)


class ConsultarClonOfflineTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memoria_dir = os.path.join(self.test_dir, "memories")
        os.makedirs(self.memoria_dir, exist_ok=True)

        from dep_desarrollo import motor_clonacion
        self._original_memory_dir = motor_clonacion.MEMORY_DIR
        motor_clonacion.MEMORY_DIR = self.memoria_dir
        self.motor = motor_clonacion

    def tearDown(self):
        self.motor.MEMORY_DIR = self._original_memory_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_consulta_offline_retorna_respuesta(self):
        datos = self.motor.cargar_datos()
        clon = datos["clones"]["rsanchez_cobol"]
        respuesta = self.motor.consultar_clon_offline(clon, "¿Qué es COBOL?", "test-s")
        self.assertIsInstance(respuesta, str)
        self.assertGreater(len(respuesta), 0)

    def test_consulta_offline_incluye_nombre(self):
        datos = self.motor.cargar_datos()
        clon = datos["clones"]["ana_finanzas"]
        respuesta = self.motor.consultar_clon_offline(clon, "¿Cómo ahorrar?", "test-s")
        self.assertIn("Ana", respuesta)


if __name__ == "__main__":
    unittest.main()
