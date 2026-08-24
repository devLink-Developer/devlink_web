from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class FrontendContractTests(SimpleTestCase):
    def test_base_loads_shared_styles_and_brand(self):
        source = (
            Path(settings.BASE_DIR) / "templates" / "base.html"
        ).read_text(encoding="utf-8")

        self.assertIn("{% load static %}", source)
        self.assertIn("{% static 'styles.css' %}", source)
        self.assertIn("DevLink", source)

    def test_styles_expose_brand_and_accessibility_tokens(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8")

        for token in ("--brand-900", "--brand-600", "--accent-500", "--focus-ring"):
            self.assertIn(token, css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(":focus-visible", css)

    def test_styles_define_shared_shell_and_component_contract(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8")

        for token in ("--surface-canvas", "--text-primary", "--radius-panel"):
            self.assertIn(token, css)
        for selector in (
            ".app-shell",
            ".app-header",
            ".page-shell",
            ".panel",
            ".button",
            ".field",
            ".data-table",
            ".alert",
        ):
            self.assertIn(selector, css)
