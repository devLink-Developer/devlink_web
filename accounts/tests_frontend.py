from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
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

    def test_public_reading_surfaces_use_shared_styles(self):
        for route in (
            "/politicas-privacidad/",
            "/terminos-servicio/",
            "/aviso-iluminacion/",
        ):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "styles.css")

    def test_login_keeps_authentication_fields(self):
        response = self.client.get("/portal/")

        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_login_exposes_accessible_auth_layout(self):
        source = self.client.get("/portal/").content.decode("utf-8")

        self.assertIn('<main class="auth-layout">', source)
        self.assertIn(
            '<section class="auth-intro" aria-labelledby="portal-title">',
            source,
        )
        self.assertIn('<h1 id="portal-title">Portal Cliente</h1>', source)
        self.assertIn('<section class="auth-panel"', source)

    def test_documentation_exposes_accessible_reading_layout(self):
        source = render_to_string("documentacion.html")

        self.assertIn('<main class="reading-layout docs-layout">', source)
        self.assertIn(
            '<aside class="reading-sidebar docs-sidebar"',
            source,
        )
        self.assertIn('<details class="reading-index" open>', source)
        self.assertIn('aria-label="Temas de documentación"', source)
        self.assertEqual(source.count('class="doc-article article-shell"'), 2)

    def test_legal_surfaces_expose_accessible_reading_layout(self):
        for route in (
            "/politicas-privacidad/",
            "/terminos-servicio/",
            "/aviso-iluminacion/",
        ):
            with self.subTest(route=route):
                source = self.client.get(route).content.decode("utf-8")
                self.assertIn(
                    '<main class="documentation reading-layout legal-layout">',
                    source,
                )
                self.assertIn('<aside class="reading-sidebar"', source)
                self.assertIn('<details class="reading-index" open>', source)
                self.assertIn('aria-label="Índice de contenidos"', source)
                self.assertIn('class="doc-article article-shell"', source)

    def test_auth_and_reading_layouts_have_responsive_shared_styles(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8")

        for selector in (
            ".auth-layout",
            ".auth-panel",
            ".reading-layout",
            ".reading-sidebar",
            ".article-shell",
            ".legal-layout",
        ):
            self.assertIn(selector, css)
        self.assertRegex(
            css,
            r"(?s)@media \(max-width: 899px\).*?\.reading-index",
        )

    def test_reading_indices_collapse_on_mobile_and_expose_active_location(self):
        sources = [
            render_to_string("documentacion.html"),
            self.client.get("/politicas-privacidad/").content.decode("utf-8"),
            self.client.get("/terminos-servicio/").content.decode("utf-8"),
            self.client.get("/aviso-iluminacion/").content.decode("utf-8"),
        ]

        for source in sources:
            title = source.split("<title>", 1)[1].split("</title>", 1)[0]
            with self.subTest(title=title):
                self.assertIn("window.matchMedia('(max-width: 899px)')", source)
                self.assertIn("readingIndex.removeAttribute('open')", source)
                self.assertIn("link.setAttribute('aria-current', 'location')", source)
                self.assertIn("link.removeAttribute('aria-current')", source)

    def test_content_page_mobile_toggle_keeps_three_visible_strokes(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8")
        toggle_rule = css.split(".content-page .nav-toggle {", 1)[1].split("}", 1)[0]
        stroke_rule = css.split(".content-page .nav-toggle span {", 1)[1].split("}", 1)[0]

        self.assertIn("flex-direction: column;", toggle_rule)
        self.assertIn("flex: 0 0 auto;", stroke_rule)

    def test_article_reading_targets_clear_the_fixed_header(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8")

        self.assertRegex(
            css,
            r"(?s)section\[id\],\s*\.article-shell\[id\]\s*\{.*?"
            r"scroll-margin-top:\s*calc\(var\(--header-height\) \+ 16px\);",
        )

    def test_mobile_reading_links_move_focus_out_of_collapsed_index(self):
        sources = [
            render_to_string("documentacion.html"),
            self.client.get("/politicas-privacidad/").content.decode("utf-8"),
            self.client.get("/terminos-servicio/").content.decode("utf-8"),
            self.client.get("/aviso-iluminacion/").content.decode("utf-8"),
        ]

        for source in sources:
            title = source.split("<title>", 1)[1].split("</title>", 1)[0]
            with self.subTest(title=title):
                self.assertIn("function focusReadingTarget(target)", source)
                self.assertIn("const originalTabindex = focusTarget.getAttribute('tabindex')", source)
                self.assertIn("focusTarget.setAttribute('tabindex', '-1')", source)
                self.assertIn("focusTarget.focus({ preventScroll: true })", source)
                self.assertIn("focusTarget.removeAttribute('tabindex')", source)
                self.assertRegex(
                    source,
                    r"(?s)if \(readingBreakpoint\.matches\).*?"
                    r"readingIndex\.removeAttribute\('open'\);.*?"
                    r"requestAnimationFrame\(\(\) => \{.*?"
                    r"focusReadingTarget\(target\)",
                )

    def test_programmatic_reading_scroll_respects_reduced_motion(self):
        sources = [
            render_to_string("documentacion.html"),
            self.client.get("/politicas-privacidad/").content.decode("utf-8"),
            self.client.get("/terminos-servicio/").content.decode("utf-8"),
            self.client.get("/aviso-iluminacion/").content.decode("utf-8"),
        ]

        for source in sources:
            title = source.split("<title>", 1)[1].split("</title>", 1)[0]
            with self.subTest(title=title):
                self.assertIn(
                    "window.matchMedia('(prefers-reduced-motion: reduce)')",
                    source,
                )
                self.assertIn(
                    "behavior: reducedMotion.matches ? 'auto' : 'smooth'",
                    source,
                )

    def test_dashboard_templates_keep_critical_bindings(self):
        root = Path(settings.BASE_DIR) / "templates" / "dashboard"
        expectations = {
            "main.html": ("client_products", "website_url", "logout"),
            "whatsapp_report.html": ("page_obj", "total_consultas", "fecha_reporte"),
            "edit_questions.html": ("respuesta_id", "nueva_respuesta", "save-question"),
        }

        for name, needles in expectations.items():
            source = (root / name).read_text(encoding="utf-8")
            for needle in needles:
                with self.subTest(template=name, binding=needle):
                    self.assertIn(needle, source)

    def test_dashboard_templates_expose_shared_operational_layout(self):
        root = Path(settings.BASE_DIR) / "templates" / "dashboard"
        main_source = (root / "main.html").read_text(encoding="utf-8")
        report_source = (root / "whatsapp_report.html").read_text(encoding="utf-8")
        editor_source = (root / "edit_questions.html").read_text(encoding="utf-8")
        css = (Path(settings.BASE_DIR) / "static" / "styles.css").read_text(
            encoding="utf-8"
        )

        for source in (main_source, report_source, editor_source):
            self.assertIn('class="app-shell', source)
            self.assertIn('class="app-header', source)
            self.assertIn('class="dashboard-shell', source)
            self.assertIn('class="page-heading', source)

        self.assertIn('class="metric-grid', main_source)
        self.assertIn('class="product-list', main_source)
        self.assertIn('class="metric-grid', report_source)
        self.assertIn('class="report-table', report_source)
        self.assertIn('class="editor-list', editor_source)
        self.assertIn('aria-modal="true"', editor_source)
        self.assertIn('aria-labelledby="modalTitle"', editor_source)

        for selector in (
            ".dashboard-shell",
            ".metric-grid",
            ".product-list",
            ".report-table",
            ".editor-list",
        ):
            self.assertIn(selector, css)

    def test_dashboard_mobile_shell_uses_a_valid_contained_width(self):
        css = (Path(settings.BASE_DIR) / "static" / "styles.css").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "width: min(calc(100% - 1.25rem), var(--content-width));",
            css,
        )
        self.assertIn(".product-item__copy > p {", css)
        self.assertIn("overflow-wrap: anywhere;", css)
