from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.messages import get_messages
from django.test import SimpleTestCase, override_settings


@override_settings(
    SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies"
)
class HomeContactLanguageTests(SimpleTestCase):
    @patch("django.core.mail.send_mail")
    @patch("accounts.models.ContactRequest.objects.create")
    def test_contact_confirmation_uses_the_selected_language(
        self,
        create_contact,
        _send_mail,
    ):
        create_contact.return_value = SimpleNamespace(id=1)
        cases = (
            (
                "es",
                "¡Gracias por contactarnos! Te responderemos en menos de 24 horas.",
            ),
            (
                "en",
                "Thank you for contacting us! We will reply within 24 hours.",
            ),
            (
                "pt-BR",
                "Agradecemos o contato! Responderemos em até 24 horas.",
            ),
        )

        for language, expected_message in cases:
            with self.subTest(language=language):
                self.client.cookies.clear()
                response = self.client.post(
                    "/",
                    {
                        "nombre": "Test User",
                        "email": "test@example.com",
                        "empresa": "Example",
                        "proyecto": "Test project",
                        "language": language,
                    },
                )
                self.assertRedirects(
                    response,
                    f"/?lang={language}#contacto",
                    fetch_redirect_response=False,
                )
                self.assertEqual(
                    [str(message) for message in get_messages(response.wsgi_request)],
                    [expected_message],
                )

    @patch("django.core.mail.send_mail")
    @patch("accounts.models.ContactRequest.objects.create")
    def test_contact_confirmation_falls_back_to_spanish(
        self,
        create_contact,
        _send_mail,
    ):
        create_contact.return_value = SimpleNamespace(id=1)
        response = self.client.post(
            "/",
            {
                "nombre": "Test User",
                "email": "test@example.com",
                "proyecto": "Test project",
                "language": "unsupported",
            },
        )

        self.assertRedirects(
            response,
            "/?lang=es#contacto",
            fetch_redirect_response=False,
        )
