from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.messages import get_messages
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


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


class AdminNavigationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="navigation-admin",
            email="navigation-admin@example.com",
            password="test-password-only",
        )

    def test_public_site_shows_admin_panel_link_for_superuser_session(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("home"))

        self.assertContains(response, 'href="/admin-panel/"')
        self.assertContains(response, 'data-i18n="nav.admin"')
        self.assertNotContains(response, 'data-i18n="nav.portal"')

    def test_public_site_keeps_client_portal_for_anonymous_visitors(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'data-i18n="nav.portal"')
        self.assertNotContains(response, 'data-i18n="nav.admin"')

    def test_admin_dashboard_links_back_to_public_site(self):
        rendered = render_to_string(
            "admin_panel/dashboard.html",
            {
                "user": self.admin,
                "total_users": 0,
                "active_users": 0,
                "total_products": 0,
                "active_products": 0,
                "total_contacts": 0,
                "pending_contacts": 0,
                "recent_users": [],
            },
        )

        self.assertIn('href="/"', rendered)
        self.assertIn("Ver sitio", rendered)


class BrandAssetTests(SimpleTestCase):
    public_templates = (
        "index.html",
        "accounts/login.html",
        "documentacion.html",
        "aviso-iluminacion.html",
        "politicas-privacidad.html",
        "terminos-servicio.html",
        "billing/base.html",
    )

    def test_public_pages_serve_brand_assets_from_devlink(self):
        for template_name in self.public_templates:
            with self.subTest(template=template_name):
                rendered = render_to_string(template_name)
                self.assertNotIn("ss-static-001.esmsv.com", rendered)
                self.assertIn(
                    'href="/static/images/devlink-logo-email.png"',
                    rendered,
                )

    def test_marketing_page_uses_the_local_logo_in_header_and_footer(self):
        rendered = render_to_string("index.html")

        self.assertEqual(
            rendered.count('src="/static/images/devlink-logo-email.png"'),
            2,
        )


class SocialLinkTests(SimpleTestCase):
    def test_public_instagram_links_use_the_official_devlink_profile(self):
        for template_name in ("index.html", "documentacion.html", "accounts/login.html"):
            with self.subTest(template=template_name):
                rendered = render_to_string(template_name)
                self.assertIn('href="https://www.instagram.com/_devlink_/"', rendered)
                self.assertNotIn('instagram.com/devlink.com.ar', rendered)
