import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)


class GeminiClientTests(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "test-key-12345678901234567890"
        os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"

    def tearDown(self):
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GEMINI_MODEL", None)

    def test_get_model_name_default(self):
        from gemini_client import get_model_name, DEFAULT_MODEL
        os.environ.pop("GEMINI_MODEL", None)
        self.assertEqual(get_model_name(), DEFAULT_MODEL)

    def test_get_model_name_from_env(self):
        from gemini_client import get_model_name
        os.environ["GEMINI_MODEL"] = "gemini-pro"
        self.assertEqual(get_model_name(), "gemini-pro")

    def test_get_api_key(self):
        from gemini_client import get_api_key
        self.assertEqual(get_api_key(), "test-key-12345678901234567890")

    def test_get_api_key_missing(self):
        from gemini_client import get_api_key
        os.environ.pop("GEMINI_API_KEY", None)
        self.assertIsNone(get_api_key())

    def test_validate_response_structure_valid(self):
        from gemini_client import _validate_response_structure
        response = {
            "candidates": [{
                "content": {"parts": [{"text": "  Hola mundo  "}]},
                "finishReason": "STOP"
            }]
        }
        self.assertEqual(_validate_response_structure(response), "Hola mundo")

    def test_validate_response_structure_no_candidates(self):
        from gemini_client import _validate_response_structure
        self.assertIsNone(_validate_response_structure({}))

    def test_validate_response_structure_safety_block(self):
        from gemini_client import _validate_response_structure
        response = {
            "candidates": [{
                "content": {"parts": [{"text": "blocked"}]},
                "finishReason": "SAFETY"
            }]
        }
        self.assertIsNone(_validate_response_structure(response))

    def test_validate_response_structure_no_content(self):
        from gemini_client import _validate_response_structure
        response = {
            "candidates": [{"finishReason": "STOP"}]
        }
        self.assertIsNone(_validate_response_structure(response))

    def test_validate_response_structure_no_parts(self):
        from gemini_client import _validate_response_structure
        response = {
            "candidates": [{
                "content": {},
                "finishReason": "STOP"
            }]
        }
        self.assertIsNone(_validate_response_structure(response))

    def test_validate_response_structure_empty_text(self):
        from gemini_client import _validate_response_structure
        response = {
            "candidates": [{
                "content": {"parts": [{"text": "  "}]},
                "finishReason": "STOP"
            }]
        }
        self.assertIsNone(_validate_response_structure(response))

    def test_llamar_gemini_no_api_key(self):
        from gemini_client import llamar_gemini
        os.environ.pop("GEMINI_API_KEY", None)
        self.assertIsNone(llamar_gemini("test prompt"))

    @patch('gemini_client.urllib.request.urlopen')
    def test_llamar_gemini_success(self, mock_urlopen):
        from gemini_client import llamar_gemini
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": "Respuesta de prueba"}]},
                "finishReason": "STOP"
            }]
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = llamar_gemini("test prompt", temperature=0.5, max_tokens=100)
        self.assertEqual(result, "Respuesta de prueba")

    @patch('gemini_client.urllib.request.urlopen')
    def test_llamar_gemini_http_error(self, mock_urlopen):
        from gemini_client import llamar_gemini
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None, fp=MagicMock()
        )
        self.assertIsNone(llamar_gemini("test prompt"))

    @patch('gemini_client.urllib.request.urlopen')
    def test_llamar_gemini_json_mode(self, mock_urlopen):
        from gemini_client import llamar_gemini
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": '{"key": "value"}'}]},
                "finishReason": "STOP"
            }]
        }).encode('utf-8')
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = llamar_gemini("test prompt", json_mode=True)
        self.assertEqual(result, '{"key": "value"}')


class AgenteVentasGeminiMockTests(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "test-key-12345678901234567890"

    def tearDown(self):
        os.environ.pop("GEMINI_API_KEY", None)

    @patch('gemini_client.llamar_gemini')
    def test_analizar_datos_con_gemini(self, mock_llamar):
        mock_llamar.return_value = json.dumps({
            "analisis_oportunidad": "Alta demanda",
            "empresas_objetivo": ["Bancos", "Tech"],
            "correo_ventas": "Estimado director..."
        })
        from dep_marketing.agente_ventas_mercado import analizar_datos_con_gemini
        result = analizar_datos_con_gemini(["dato1"], "COBOL", "key")
        self.assertIsNotNone(result)
        self.assertEqual(result["analisis_oportunidad"], "Alta demanda")
        mock_llamar.assert_called_once()

    @patch('gemini_client.llamar_gemini')
    def test_analizar_datos_con_gemini_none_response(self, mock_llamar):
        mock_llamar.return_value = None
        from dep_marketing.agente_ventas_mercado import analizar_datos_con_gemini
        result = analizar_datos_con_gemini(["dato1"], "COBOL", "key")
        self.assertIsNone(result)


class MotorClonacionGeminiMockTests(unittest.TestCase):
    def setUp(self):
        os.environ["GEMINI_API_KEY"] = "test-key-12345678901234567890"

    def tearDown(self):
        os.environ.pop("GEMINI_API_KEY", None)

    @patch('gemini_client.llamar_gemini')
    def test_consultar_clon_online_success(self, mock_llamar):
        mock_llamar.return_value = "Respuesta del experto en COBOL"
        from dep_desarrollo.motor_clonacion import consultar_clon_online
        clon = {
            "nombre": "Roberto Sánchez",
            "especialidad": "COBOL",
            "conocimiento": "Conocimiento de COBOL para banca."
        }
        result = consultar_clon_online(clon, "¿Qué es COBOL?", "key")
        self.assertEqual(result, "Respuesta del experto en COBOL")

    @patch('gemini_client.llamar_gemini')
    def test_consultar_clon_online_fallback_offline(self, mock_llamar):
        mock_llamar.return_value = None
        from dep_desarrollo.motor_clonacion import consultar_clon_online
        clon = {
            "nombre": "Roberto Sánchez",
            "especialidad": "COBOL",
            "conocimiento": "COBOL es un lenguaje de programación para banca."
        }
        result = consultar_clon_online(clon, "¿Qué es COBOL?", "key")
        self.assertIsNotNone(result)
        self.assertIn("Roberto Sánchez", result)


if __name__ == "__main__":
    unittest.main()
