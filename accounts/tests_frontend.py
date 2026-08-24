from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings


class NavigationContractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nav_attributes = {}
        self.toggle_attributes = {}
        self.nav_link_count = 0
        self._inside_navigation = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "button" and "data-nav-toggle" in attributes:
            self.toggle_attributes = attributes
        if tag == "nav" and "data-nav" in attributes:
            self.nav_attributes = attributes
            self._inside_navigation = True
        elif tag == "a" and self._inside_navigation:
            self.nav_link_count += 1

    def handle_endtag(self, tag):
        if tag == "nav" and self._inside_navigation:
            self._inside_navigation = False


@override_settings(STATIC_ROOT=Path(settings.BASE_DIR) / "static")
class FrontendContractTests(SimpleTestCase):
    def test_home_preserves_sections_and_contact_fields(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for section_id in (
            "inicio",
            "servicios",
            "suite-lite",
            "soluciones",
            "metodologia",
            "contacto",
        ):
            self.assertContains(response, f'id="{section_id}"')
        for field in ("nombre", "email", "empresa", "proyecto", "newsletter"):
            self.assertContains(response, f'name="{field}"')

    def test_home_exposes_marketing_layout_contract(self):
        response = self.client.get("/")
        source = response.content.decode("utf-8")

        self.assertIn('<body class="marketing-page">', source)
        self.assertRegex(
            source,
            r'<body class="marketing-page">\s*<!--\s*THESIS:',
        )
        self.assertIn("FORM: Estándar SaaS tecnológico; seed key ee6c512a.", source)
        self.assertIn(
            "FINISH: unreviewed and undocumented is unfinished; this build ends "
            "with the finish review, the verdict, DESIGN.md, and every shipping "
            "raster carrying its provenance",
            source,
        )
        for class_name in (
            "section-shell",
            "capability-map",
            "service-grid",
            "suite-products",
            "process-steps",
            "contact-grid",
        ):
            self.assertIn(class_name, source)
        for attribute in ("data-header", "data-nav-toggle", "data-nav"):
            self.assertIn(attribute, source)

    def test_mobile_navigation_supports_escape_dismissal(self):
        source = (
            Path(settings.BASE_DIR) / "templates" / "index.html"
        ).read_text(encoding="utf-8")

        self.assertIn("event.key === 'Escape'", source)
        self.assertIn("navToggle.focus()", source)

    def test_navigation_progressively_enhances_focus_management(self):
        response = self.client.get("/")
        parser = NavigationContractParser()
        source = response.content.decode("utf-8")
        parser.feed(source)

        self.assertGreater(parser.nav_link_count, 0)
        self.assertNotIn("inert", parser.nav_attributes)
        self.assertEqual(parser.toggle_attributes["aria-expanded"], "false")
        self.assertEqual(
            parser.toggle_attributes["aria-controls"],
            parser.nav_attributes["id"],
        )
        self.assertIn("nav.inert = !desktopNavigation.matches && !isOpen", source)
        self.assertIn("setNavigationState(false)", source)

        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            css,
            r"(?s)@media \(max-width: 959px\).*?\.nav-links \{.*?"
            r"visibility: hidden;.*?\.nav-links\.is-open \{.*?"
            r"visibility: visible;",
        )
        self.assertRegex(
            css,
            r"(?s)@media \(min-width: 960px\).*?\.nav-links \{.*?"
            r"visibility: visible;",
        )

    def test_service_icons_use_the_existing_decorative_icon_family(self):
        source = self.client.get("/").content.decode("utf-8")

        for emoji in ("📦", "🤝", "⚙️", "💬"):
            self.assertNotIn(emoji, source)
        self.assertEqual(source.count('class="service-icon" aria-hidden="true"'), 4)
        for icon in ("fa-database", "fa-handshake", "fa-gears", "fa-comments"):
            self.assertIn(icon, source)
        self.assertIn("font-awesome/6.0.0/css/all.min.css", source)

    def test_marketing_hero_uses_a_solid_non_luminous_surface(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8")
        hero_rule = css.split(".marketing-page .hero {", 1)[1].split("}", 1)[0]

        self.assertIn("background: var(--surface-white);", hero_rule)
        self.assertNotIn("radial-gradient", hero_rule)

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
