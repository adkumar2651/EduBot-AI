import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

import httpx
from openai import APIConnectionError, AuthenticationError

import backend.app as backend_module


class ChatApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_config = {
            key: backend_module.app.config.get(key)
            for key in ("TESTING", "GROQ_API_KEY", "RATELIMIT_ENABLED")
        }
        backend_module.app.config.update(
            TESTING=True,
            GROQ_API_KEY="test-key",
            RATELIMIT_ENABLED=False,
        )

    @classmethod
    def tearDownClass(cls):
        backend_module.app.config.update(cls.original_config)

    def setUp(self):
        self.client = backend_module.app.test_client()

    def test_health_endpoints_do_not_expose_credentials(self):
        for path in ("/health", "/api/health"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["status"], "ok")
            self.assertTrue(response.json["ai_configured"])
            self.assertNotIn("test-key", response.get_data(as_text=True))

    def test_general_questions_in_english_hindi_and_hinglish_reach_groq(self):
        questions = (
            "What is Artificial Intelligence?",
            "How do I reverse a string in Java?",
            "कृत्रिम बुद्धिमत्ता क्या है?",
            "AI ka use education mein kaise hota hai?",
            "What is the capital of Japan?",
        )
        with patch.object(backend_module, "groq_response", return_value="model response") as provider:
            for question in questions:
                response = self.client.post("/api/chat", json={"message": question})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["response"], "model response")
                self.assertEqual(response.json["source"], "groq")
        self.assertEqual(provider.call_count, len(questions))

    def test_recent_conversation_history_is_forwarded_to_groq(self):
        history = [
            {"role": "user", "content": "Explain a Java interface."},
            {"role": "assistant", "content": "An interface defines a contract."},
        ]
        with patch.object(backend_module, "groq_response", return_value="It allows multiple implementations.") as provider:
            response = self.client.post(
                "/api/chat",
                json={"message": "Can you give an example?", "history": history},
            )
        self.assertEqual(response.status_code, 200)
        messages = provider.call_args.args[0]
        self.assertEqual(messages[1:3], history)
        self.assertEqual(messages[-1], {"role": "user", "content": "Can you give an example?"})

    def test_invalid_requests_and_visitor_credentials_are_rejected(self):
        for payload in ({}, {"message": " "}, {"message": "Hi", "api_key": "visitor-value"}):
            with self.subTest(payload=payload):
                response = self.client.post("/api/chat", json=payload)
                self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/chat", data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_missing_owner_key_returns_configuration_error(self):
        backend_module.app.config["GROQ_API_KEY"] = ""
        try:
            response = self.client.post("/api/chat", json={"message": "What is AI?"})
        finally:
            backend_module.app.config["GROQ_API_KEY"] = "test-key"
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "ai_not_configured")
        self.assertNotIn("response", response.json)

    def test_invalid_provider_credentials_are_reported_safely(self):
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        provider_response = httpx.Response(401, request=request)
        auth_error = AuthenticationError(
            "Invalid credentials",
            response=provider_response,
            body=None,
        )
        with patch.object(backend_module, "OpenAI") as client_class:
            client_class.return_value.chat.completions.create.side_effect = auth_error
            response = self.client.post("/api/chat", json={"message": "What is AI?"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["code"], "ai_invalid_credentials")
        self.assertNotIn("Invalid credentials", response.get_data(as_text=True))

    def test_provider_downtime_returns_an_error_not_a_fallback_answer(self):
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        connection_error = APIConnectionError(request=request)
        with patch.object(backend_module, "OpenAI") as client_class:
            client_class.return_value.chat.completions.create.side_effect = connection_error
            response = self.client.post("/api/chat", json={"message": "What is AI?"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "ai_unavailable")
        self.assertNotIn("response", response.json)

    def test_chat_request_size_is_limited(self):
        response = self.client.post(
            "/api/chat",
            data='{"message":"' + ("x" * (65 * 1024)) + '"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 413)

    def test_chat_rate_limit_is_enforced(self):
        backend_module.app.config["RATELIMIT_ENABLED"] = True
        try:
            with patch.object(backend_module, "groq_response", return_value="model response") as provider:
                for _ in range(15):
                    response = self.client.post(
                        "/api/chat",
                        json={"message": "What is AI?"},
                        environ_overrides={"REMOTE_ADDR": "198.51.100.10"},
                    )
                    self.assertEqual(response.status_code, 200)
                response = self.client.post(
                    "/api/chat",
                    json={"message": "What is AI?"},
                    environ_overrides={"REMOTE_ADDR": "198.51.100.10"},
                )
            self.assertEqual(response.status_code, 429)
            self.assertEqual(provider.call_count, 15)
        finally:
            backend_module.app.config["RATELIMIT_ENABLED"] = False

    def test_pdf_upload_is_public_and_validates_file_type(self):
        response = self.client.post("/api/upload/pdf")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["code"], "missing_file")

        response = self.client.post(
            "/api/upload/pdf",
            data={"file": (BytesIO(b"not a pdf"), "notes.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["code"], "invalid_file")

    def test_pdf_upload_uses_the_central_groq_service(self):
        pdf = MagicMock()
        pdf.pages = [MagicMock()]
        pdf.pages[0].extract_text.return_value = "Course notes about neural networks."
        pdf_context = MagicMock()
        pdf_context.__enter__.return_value = pdf
        pdfplumber = MagicMock()
        pdfplumber.open.return_value = pdf_context

        with (
            patch.dict("sys.modules", {"pdfplumber": pdfplumber}),
            patch.object(backend_module, "PDF_AVAILABLE", True),
            patch.object(backend_module, "groq_response", return_value="A real summary.") as provider,
        ):
            response = self.client.post(
                "/api/upload/pdf",
                data={"file": (BytesIO(b"%PDF-1.4"), "notes.pdf")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["summary"], "A real summary.")
        self.assertEqual(response.json["pages"], 1)
        self.assertIn("Course notes about neural networks.", provider.call_args.args[0][-1]["content"])

    def test_root_entry_point_reexports_the_canonical_app(self):
        from app import app as root_app

        self.assertIs(root_app, backend_module.app)


if __name__ == "__main__":
    unittest.main()
