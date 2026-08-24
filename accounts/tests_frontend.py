import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

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


class EmailTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._tables = []
        self._cells = []
        self._cta_cell_context = []
        self._anchor_context = []
        self.tables = []
        self.first_logo_cell_styles = []
        self.cta_cells = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "table":
            self._tables.append({"attrs": attributes, "has_th": False})
        elif tag == "th" and self._tables:
            self._tables[-1]["has_th"] = True
        if tag == "td":
            self._cells.append(attributes)
            classes = set(attributes.get("class", "").split())
            cta_cell = (
                {"attrs": attributes, "anchors": []}
                if {"stack", "cta-cell"}.issubset(classes)
                else None
            )
            self._cta_cell_context.append(cta_cell)
            if cta_cell:
                self.cta_cells.append(cta_cell)
        elif tag == "a":
            cta_cell = next(
                (
                    cell
                    for cell in reversed(self._cta_cell_context)
                    if cell is not None
                ),
                None,
            )
            anchor = {"attrs": attributes, "text": []} if cta_cell else None
            self._anchor_context.append(anchor)
            if anchor:
                cta_cell["anchors"].append(anchor)
        elif (
            tag == "img"
            and attributes.get("alt") == "devLink"
            and not self.first_logo_cell_styles
        ):
            self.first_logo_cell_styles = [
                cell.get("style", "") for cell in reversed(self._cells)
            ]

    def handle_endtag(self, tag):
        if tag == "table" and self._tables:
            self.tables.append(self._tables.pop())
        elif tag == "td" and self._cells:
            self._cells.pop()
            self._cta_cell_context.pop()
        elif tag == "a" and self._anchor_context:
            self._anchor_context.pop()

    def handle_data(self, data):
        if self._anchor_context and self._anchor_context[-1]:
            self._anchor_context[-1]["text"].append(data)


@override_settings(STATIC_ROOT=Path(settings.BASE_DIR) / "static")
class FrontendContractTests(SimpleTestCase):
    def test_email_templates_keep_brand_and_contact_links(self):
        root = Path(settings.BASE_DIR) / "templates"
        template_names = (
            "email-bienvenida.html",
            "email-preview.html",
            "email-campana-servicios-inline.html",
            "email-campana-suite-lite-inline.html",
            "email-campana-chatbot-webapp.html",
        )
        expected_site_links = {
            "email-bienvenida.html": (
                "https://devlink.com.ar/documentacion",
                "https://devlink.com.ar",
                "https://devlink.com.ar/documentacion",
            ),
            "email-preview.html": (
                "https://devlink.com.ar/documentacion",
                "https://devlink.com.ar",
                "https://devlink.com.ar/documentacion",
            ),
            "email-campana-servicios-inline.html": (
                "https://devlink.com.ar/#contacto",
                "https://devlink.com.ar",
            ),
            "email-campana-suite-lite-inline.html": (
                "https://devlink.com.ar",
                "https://devlink.com.ar/#contacto",
                "https://devlink.com.ar",
            ),
            "email-campana-chatbot-webapp.html": (
                "https://devlink.com.ar/#contacto",
                "https://devlink.com.ar",
            ),
        }
        for name in template_names:
            source = (root / name).read_text(encoding="utf-8")
            self.assertIn("devLink", source)
            self.assertIn('href="mailto:info@devlink.com.ar"', source)
            logo_sources = re.findall(
                r'<img\b(?=[^>]*\balt="devLink")[^>]*\bsrc="([^"]+)"',
                source,
            )
            self.assertTrue(logo_sources)
            self.assertEqual(
                set(logo_sources),
                {"https://devlink.com.ar/static/images/devlink-logo-email.png"},
            )
            self.assertNotIn("i.pinimg.com", source)
            for color in ("#07162d", "#1264f6", "#06d6ff"):
                self.assertIn(color, source.lower())
            hrefs = re.findall(r'href="([^"]+)"', source)
            site_links = tuple(
                href
                for href in hrefs
                if urlparse(href).hostname
                in {"devlink.com.ar", "www.devlink.com.ar"}
            )
            self.assertEqual(site_links, expected_site_links[name])
            self.assertRegex(
                source,
                r'<table[^>]+role="presentation"[^>]+width="(?:100%|600)"',
            )
            parser = EmailTableParser()
            parser.feed(source)
            shell_styles = [
                self._inline_style(table["attrs"].get("style", ""))
                for table in parser.tables
                if table["attrs"].get("role") == "presentation"
                and table["attrs"].get("width") == "600"
            ]
            self.assertTrue(
                any(
                    style.get("width") == "100%"
                    and style.get("max-width") == "600px"
                    and (
                        style.get("background") == "#ffffff"
                        or style.get("background-color") == "#ffffff"
                    )
                    for style in shell_styles
                )
            )
            self.assertTrue(
                any(
                    self._padding_is_adequate(style.get("padding", ""))
                    and (
                        style.get("background") == "#07162d"
                        or style.get("background-color") == "#07162d"
                    )
                    for style in map(
                        self._inline_style, parser.first_logo_cell_styles
                    )
                )
            )

        responsive_contracts = {
            "email-bienvenida.html": (
                r"\.email-shell\{[^}]*padding:0!important",
                r"\.section-padding\{[^}]*padding-left:20px!important;"
                r"[^}]*padding-right:20px!important",
            ),
            "email-preview.html": (
                r"\.preview-section\{[^}]*padding-left:20px!important;"
                r"[^}]*padding-right:20px!important",
            ),
            "email-campana-servicios-inline.html": (
                r"\.email-shell\{[^}]*padding:0!important",
            ),
            "email-campana-suite-lite-inline.html": (
                r"\.email-shell\{[^}]*padding:0!important",
                r"\.section-padding\{[^}]*padding-left:24px!important;"
                r"[^}]*padding-right:24px!important",
            ),
            "email-campana-chatbot-webapp.html": (
                r"\.email-shell\{[^}]*padding:0!important",
                r"\.section\{[^}]*padding-left:24px!important;"
                r"[^}]*padding-right:24px!important",
                r"\.stack\{[^}]*display:block!important;[^}]*width:100%!important;"
                r"[^}]*padding:8px0!important",
            ),
        }
        for name, contracts in responsive_contracts.items():
            mobile_css = "".join(
                self._mobile_media_blocks(
                    (root / name).read_text(encoding="utf-8")
                )
            )
            self.assertTrue(mobile_css)
            for contract in contracts:
                self.assertRegex(mobile_css, contract)

        for name in ("email-bienvenida.html", "email-preview.html"):
            parser = EmailTableParser()
            parser.feed((root / name).read_text(encoding="utf-8"))
            pricing_tables = [table for table in parser.tables if table["has_th"]]
            layout_tables = [table for table in parser.tables if not table["has_th"]]
            self.assertTrue(pricing_tables)
            self.assertTrue(
                all(table["attrs"].get("role") != "presentation" for table in pricing_tables)
            )
            self.assertTrue(layout_tables)
            self.assertTrue(
                all(
                    table["attrs"].get("role") == "presentation"
                    for table in layout_tables
                )
            )

        chatbot = (root / "email-campana-chatbot-webapp.html").read_text(
            encoding="utf-8"
        )
        parser = EmailTableParser()
        parser.feed(chatbot)
        self.assertGreaterEqual(len(parser.cta_cells), 2)
        for cta_cell in parser.cta_cells:
            self.assertTrue(
                any(
                    anchor["attrs"].get("href", "").startswith("https://")
                    and "".join(anchor["text"]).strip()
                    for anchor in cta_cell["anchors"]
                )
            )
        self.assertRegex(
            chatbot.replace(" ", ""),
            r'\.cta-cell\{[^}]*display:block!important;[^}]*width:100%!important;'
            r'[^}]*padding:0!important',
        )

        footer_fragments = {
            "email-bienvenida.html": (
                root / "email-bienvenida.html"
            ).read_text(encoding="utf-8").rsplit(
                '<tr><td class="section-padding"', 1
            )[1],
            "email-preview.html": (
                root / "email-preview.html"
            ).read_text(encoding="utf-8").rsplit(
                '<tr><td class="preview-section"', 1
            )[1].split("</td></tr>", 1)[0],
            "email-campana-servicios-inline.html": (
                root / "email-campana-servicios-inline.html"
            ).read_text(encoding="utf-8").split("<!-- Footer -->", 1)[1],
            "email-campana-suite-lite-inline.html": (
                root / "email-campana-suite-lite-inline.html"
            ).read_text(encoding="utf-8").rsplit(
                '<tr><td class="section-padding"', 1
            )[1],
            "email-campana-chatbot-webapp.html": (
                root / "email-campana-chatbot-webapp.html"
            ).read_text(encoding="utf-8").rsplit(
                '<tr><td class="section"', 1
            )[1],
        }
        for name, footer in footer_fragments.items():
            background = re.search(
                r"background(?:-color)?:\s*(#[0-9a-fA-F]{6})", footer
            ).group(1)
            foregrounds = re.findall(
                r"(?<![-\w])color:\s*(#[0-9a-fA-F]{6})", footer
            )
            self.assertTrue(foregrounds)
            for foreground in foregrounds:
                with self.subTest(template=name, foreground=foreground):
                    self.assertGreaterEqual(
                        self._contrast_ratio(foreground, background), 4.5
                    )

    @staticmethod
    def _inline_style(source):
        return {
            property_name.strip().lower(): value.strip().lower()
            for declaration in source.split(";")
            if ":" in declaration
            for property_name, value in (declaration.split(":", 1),)
        }

    @staticmethod
    def _padding_is_adequate(source, minimum_px=20):
        tokens = source.lower().split()
        if not 1 <= len(tokens) <= 4:
            return False
        values = []
        for token in tokens:
            if token == "0":
                values.append(0)
                continue
            match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)px", token)
            if not match:
                return False
            values.append(float(match.group(1)))
        return all(value >= minimum_px for value in values)

    @staticmethod
    def _mobile_media_blocks(source):
        compact = re.sub(r"\s+", "", source)
        blocks = []
        for match in re.finditer(
            r"@media(?:(?:only)?screenand)?\(max-width:[0-9]+px\)\{",
            compact,
            re.IGNORECASE,
        ):
            depth = 1
            index = match.end()
            while index < len(compact) and depth:
                if compact[index] == "{":
                    depth += 1
                elif compact[index] == "}":
                    depth -= 1
                index += 1
            if depth == 0:
                blocks.append(compact[match.end():index - 1])
        return blocks

    @staticmethod
    def _contrast_ratio(foreground, background):
        def luminance(color):
            channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                channel / 12.92
                if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
        return (light + 0.05) / (dark + 0.05)

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

    def test_suite_lite_collection_is_unordered_and_preserves_content(self):
        source = (
            Path(settings.BASE_DIR) / "templates" / "index.html"
        ).read_text(encoding="utf-8")
        suite = source.split('id="suite-lite"', 1)[1].split(
            'id="soluciones"', 1
        )[0]
        products = (
            (
                "Lite-POS",
                "Un punto de venta sólido para agilizar la atención, controlar "
                "cada operación y trabajar integrado con SAP.",
            ),
            (
                "Lite-Core",
                "El centro de administración del POS para mantener productos, "
                "precios, usuarios y datos bajo control.",
            ),
            (
                "Lite-Logistic",
                "Gestión de transporte y depósitos para organizar inventario, "
                "movimientos, entregas y recorridos.",
            ),
            (
                "Lite-eCommerce",
                "Una tienda online conectada con tus productos, precios, pedidos "
                "y disponibilidad para vender sin duplicar tareas.",
            ),
            (
                "Lite-Flow",
                "El puente que permite intercambiar información entre SAP, Suite "
                "Lite y los demás sistemas de tu empresa.",
            ),
            (
                "Lite-CRM",
                "Seguimiento simple de clientes, contactos y oportunidades para "
                "ordenar la actividad comercial.",
            ),
        )

        self.assertIn('<ul class="suite-products">', suite)
        self.assertNotIn('<ol class="suite-products">', suite)
        self.assertNotIn("suite-product-number", suite)
        self.assertIn('<ol class="process-steps">', source)
        positions = []
        for product, copy in products:
            self.assertIn(product, suite)
            self.assertIn(copy, suite)
            positions.append(suite.index(product))
        self.assertEqual(positions, sorted(positions))

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

    def test_self_hosted_ibm_plex_assets_and_css_contract(self):
        root = Path(settings.BASE_DIR)
        fonts = root / "static" / "fonts"
        expected_fonts = {
            "ibm-plex-sans-regular.woff2": "400",
            "ibm-plex-sans-medium.woff2": "500",
            "ibm-plex-sans-semibold.woff2": "600",
            "ibm-plex-sans-bold.woff2": "700",
        }
        css = (root / "static" / "styles.css").read_text(
            encoding="utf-8-sig"
        )

        for filename, weight in expected_fonts.items():
            with self.subTest(font=filename):
                path = fonts / filename
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 50_000)
                self.assertRegex(
                    css,
                    rf'(?s)@font-face\s*\{{(?:(?!\}}).)*'
                    rf'url\("fonts/{re.escape(filename)}"\)'
                    rf'(?:(?!\}}).)*font-weight:\s*{weight};'
                    rf'(?:(?!\}}).)*font-display:\s*swap;',
                )

        body_rule = css.split("body {", 1)[1].split("}", 1)[0]
        self.assertIn(
            'font-family: "IBM Plex Sans", "Segoe UI", ui-sans-serif, '
            "system-ui, sans-serif;",
            body_rule,
        )
        self.assertNotRegex(
            "\n".join(
                line
                for line in css.splitlines()
                if "@font-face" in line or "src:" in line
            ),
            r"https?://",
        )

        license_text = (fonts / "OFL.txt").read_text(encoding="utf-8")
        self.assertIn(
            'Copyright © 2017 IBM Corp. with Reserved Font Name "Plex"',
            license_text,
        )
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", license_text)
        self.assertIn("5) The Font Software", license_text)
        self.assertIn("DISCLAIMER", license_text)

        source = (fonts / "SOURCE.md").read_text(encoding="utf-8")
        self.assertIn("@ibm/plex-sans@1.1.0", source)
        for filename in expected_fonts:
            self.assertIn(filename, source)

    def test_installed_chrome_uses_self_hosted_ibm_plex_for_heading(self):
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        root = Path(settings.BASE_DIR)
        css = (root / "static" / "styles.css").read_text(
            encoding="utf-8-sig"
        )
        fonts = root / "static" / "fonts"
        requests = []

        def fulfill_devlink_asset(route):
            requests.append(route.request.url)
            path = urlparse(route.request.url).path
            if path == "/":
                route.fulfill(
                    status=200,
                    content_type="text/html",
                    body=(
                        '<!doctype html><html lang="es"><head>'
                        '<link rel="stylesheet" href="/static/styles.css">'
                        "</head><body><h1>Tecnología, solución ágil e "
                        "información para la acción</h1></body></html>"
                    ),
                )
            elif path == "/static/styles.css":
                route.fulfill(status=200, content_type="text/css", body=css)
            elif path.startswith("/static/fonts/"):
                font_path = fonts / Path(path).name
                route.fulfill(
                    status=200,
                    content_type="font/woff2",
                    body=font_path.read_bytes(),
                )
            else:
                route.abort()

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(
                    channel="chrome", headless=True
                )
            except PlaywrightError:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except PlaywrightError as error:
                    self.skipTest(
                        f"No Chromium-compatible browser available: {error}"
                    )

            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.route("https://devlink.test/**", fulfill_devlink_asset)
                page.goto("https://devlink.test/", wait_until="networkidle")
                page.evaluate("document.fonts.ready")

                heading = page.locator("h1")
                font_family = heading.evaluate(
                    "element => getComputedStyle(element).fontFamily"
                )
                loaded = heading.evaluate(
                    "element => document.fonts.check("
                    "'700 32px \\\"IBM Plex Sans\\\"', element.textContent)"
                )
                font_faces = page.evaluate(
                    "[...document.fonts].map(face => ({family: face.family, "
                    "weight: face.weight, status: face.status}))"
                )
                self.assertEqual(
                    font_family.split(",", 1)[0].strip().strip('"'),
                    "IBM Plex Sans",
                )
                self.assertTrue(loaded)
                self.assertTrue(
                    any(
                        face["family"] == "IBM Plex Sans"
                        and face["weight"] == "700"
                        and face["status"] == "loaded"
                        for face in font_faces
                    ),
                    font_faces,
                )
                self.assertTrue(
                    any("ibm-plex-sans-bold.woff2" in url for url in requests),
                    {"requests": requests, "fontFaces": font_faces},
                )
                self.assertTrue(
                    all(urlparse(url).hostname == "devlink.test" for url in requests)
                )
            finally:
                browser.close()

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

    def test_editor_escape_restores_focus_only_when_dialog_is_open(self):
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        editor_source = (
            Path(settings.BASE_DIR) / "templates" / "dashboard" / "edit_questions.html"
        ).read_text(encoding="utf-8")
        editor_script = editor_source.rsplit("<script>", 1)[1].split("</script>", 1)[0]
        harness = """
            <button id="edit-trigger" type="button"
                    onclick="abrirModal('answer-1', 'Respuesta 1', 'Texto actual', this)">
                Editar
            </button>
            <button id="outside-control" type="button">Fuera del diálogo</button>
            <div id="modalEditar" class="modal" aria-hidden="true">
                <h2 id="modalTitle">Editar Respuesta</h2>
                <form id="formEditar" action="/save/">
                    <textarea id="modalTextarea" name="nueva_respuesta"></textarea>
                    <input id="modalRespuestaId" name="respuesta_id">
                    <button type="button" class="btn-cancelar">Cancelar</button>
                    <button type="submit" class="btn-guardar">Guardar</button>
                </form>
            </div>
            <div id="mensajeExito"></div>
            <div id="mensajeError"></div>
            <script>
        """ + editor_script + "</script>"

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
            except PlaywrightError:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except PlaywrightError as error:
                    self.skipTest(f"No Chromium-compatible browser available: {error}")

            try:
                page = browser.new_page()
                page.set_content(harness)

                page.locator("#edit-trigger").click()
                self.assertTrue(
                    page.locator("#modalTextarea").evaluate(
                        "el => document.activeElement === el"
                    )
                )

                page.keyboard.press("Escape")
                self.assertTrue(
                    page.locator("#edit-trigger").evaluate(
                        "el => document.activeElement === el"
                    )
                )

                page.locator("#outside-control").click()
                page.keyboard.press("Escape")
                self.assertTrue(
                    page.locator("#outside-control").evaluate(
                        "el => document.activeElement === el"
                    )
                )

                page.evaluate("cerrarModal()")
                self.assertTrue(
                    page.locator("#outside-control").evaluate(
                        "el => document.activeElement === el"
                    )
                )
            finally:
                browser.close()

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

    def test_report_refresh_shrink_wraps_on_mobile_in_chrome(self):
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        css = (Path(settings.BASE_DIR) / "static" / "styles.css").read_text(
            encoding="utf-8-sig"
        )
        harness = """
            <body class="portal-page">
                <div class="page-heading page-heading--report">
                    <div><h1>Estadísticas de WhatsApp</h1>
                    <p>Análisis de las interacciones con tu chatbot</p></div>
                    <div class="report-refresh" aria-label="Estado de actualización">
                        <p>Última actualización: <strong>24/08/2026 02:15</strong></p>
                        <p>Actualización automática cada 3 minutos</p>
                    </div>
                </div>
            </body>
        """

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(
                    channel="chrome", headless=True
                )
            except PlaywrightError:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except PlaywrightError as error:
                    self.skipTest(
                        f"No Chromium-compatible browser available: {error}"
                    )

            try:
                for viewport in (
                    {"width": 1440, "height": 900},
                    {"width": 390, "height": 844},
                ):
                    with self.subTest(viewport=viewport["width"]):
                        page = browser.new_page(viewport=viewport)
                        try:
                            page.set_content(harness)
                            page.add_style_tag(content=css)
                            panel = page.locator(".report-refresh")
                            self.assertLessEqual(panel.bounding_box()["height"], 96)
                            overflow = page.evaluate(
                                "document.documentElement.scrollWidth - "
                                "document.documentElement.clientWidth"
                            )
                            self.assertLessEqual(overflow, 0)
                        finally:
                            page.close()
            finally:
                browser.close()

    def test_admin_templates_extend_shared_base_and_keep_csrf(self):
        root = Path(settings.BASE_DIR) / "templates" / "admin_panel"
        templates = list(root.glob("*.html"))
        self.assertGreaterEqual(len(templates), 12)
        for path in templates:
            source = path.read_text(encoding="utf-8")
            self.assertIn("{% extends 'base.html' %}", source)
        for name in (
            "user_form.html",
            "user_edit.html",
            "product_form.html",
            "product_edit.html",
            "user_confirm_delete.html",
        ):
            self.assertIn(
                "{% csrf_token %}",
                (root / name).read_text(encoding="utf-8"),
            )

    def test_admin_templates_use_shared_operational_components(self):
        root = Path(settings.BASE_DIR) / "templates" / "admin_panel"
        templates = {
            path.name: path.read_text(encoding="utf-8")
            for path in root.glob("*.html")
        }

        for name, source in templates.items():
            with self.subTest(template=name):
                self.assertIn('class="admin-shell page-shell', source)
                self.assertIn('class="admin-toolbar"', source)

        for name in (
            "users_list.html",
            "products_list.html",
            "contact_requests_list.html",
            "whatsapp_report.html",
        ):
            self.assertIn('class="data-table', templates[name])

        for name in (
            "user_form.html",
            "user_edit.html",
            "product_form.html",
            "product_edit.html",
        ):
            self.assertIn('class="form-grid', templates[name])

        self.assertIn(
            'class="danger-panel"',
            templates["user_confirm_delete.html"],
        )
        self.assertNotRegex(
            templates["whatsapp_report.html"],
            r'\sstyle="',
        )

        css = (Path(settings.BASE_DIR) / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        for selector in (
            ".admin-shell",
            ".admin-toolbar",
            ".form-grid",
            ".danger-panel",
            ".status-badge",
        ):
            self.assertIn(selector, css)

    def test_admin_mobile_table_actions_keep_accessible_names(self):
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        css = (
            Path(settings.BASE_DIR) / "static" / "styles.css"
        ).read_text(encoding="utf-8-sig")
        harness = """
            <div class="table-actions">
                <a href="#products" class="button"><i aria-hidden="true"></i><span>Productos</span></a>
                <a href="#edit" class="button"><i aria-hidden="true"></i><span>Editar</span></a>
                <a href="#view" class="button"><i aria-hidden="true"></i><span>Ver</span></a>
                <a href="#report" class="button"><i aria-hidden="true"></i><span>Reporte</span></a>
                <button type="button" class="button"><i aria-hidden="true"></i><span>Estado</span></button>
                <button type="button" class="button"><i aria-hidden="true"></i><span>Eliminar</span></button>
            </div>
        """

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
            except PlaywrightError:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except PlaywrightError as error:
                    self.skipTest(f"No Chromium-compatible browser available: {error}")

            try:
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page.set_content(harness)
                page.add_style_tag(content=css)

                for name in ("Productos", "Editar", "Ver", "Reporte"):
                    with self.subTest(control=name):
                        self.assertEqual(page.get_by_role("link", name=name).count(), 1)
                for name in ("Estado", "Eliminar"):
                    with self.subTest(control=name):
                        self.assertEqual(page.get_by_role("button", name=name).count(), 1)
            finally:
                browser.close()

    def test_admin_product_dialogs_manage_keyboard_focus(self):
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        root = Path(settings.BASE_DIR) / "templates" / "admin_panel"

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
            except PlaywrightError:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except PlaywrightError as error:
                    self.skipTest(f"No Chromium-compatible browser available: {error}")

            try:
                for name in ("user_edit.html", "user_products.html"):
                    source = (root / name).read_text(encoding="utf-8")
                    script = source.rsplit("<script>", 1)[1].split("</script>", 1)[0]
                    harness = """
                        <button id="add-trigger" type="button" onclick="showAddProductModal()">Agregar Producto</button>
                        <button id="edit-trigger" type="button" onclick="editProductStatus(7, 'active')">Cambiar Estado</button>
                        <button id="outside-control" type="button">Fuera de los diálogos</button>
                        <div id="addProductModal" class="modal" aria-hidden="true">
                            <button id="add-close" type="button" onclick="hideAddProductModal()">Cerrar</button>
                            <form id="addProductForm">
                                <select id="product_id"><option value="1">Producto</option></select>
                                <select id="status"><option value="active">Activo</option></select>
                                <button id="add-cancel" type="button" onclick="hideAddProductModal()">Cancelar</button>
                                <button id="add-submit" type="submit">Agregar</button>
                            </form>
                        </div>
                        <div id="editStatusModal" class="modal" aria-hidden="true">
                            <button id="edit-close" type="button" onclick="hideEditStatusModal()">Cerrar</button>
                            <form id="editStatusForm">
                                <input type="hidden" id="client_product_id" name="client_product_id">
                                <select id="new_status"><option value="active">Activo</option></select>
                                <button id="edit-cancel" type="button" onclick="hideEditStatusModal()">Cancelar</button>
                                <button id="edit-submit" type="submit">Actualizar</button>
                            </form>
                        </div>
                        <script>
                    """ + script + "</script>"

                    page = browser.new_page()
                    try:
                        page.set_content(harness)
                        page.evaluate("""
                            window.focusAtDialogHide = [];
                            for (const dialog of document.querySelectorAll('.modal')) {
                                new MutationObserver(() => {
                                    if (!dialog.classList.contains('active')) {
                                        window.focusAtDialogHide.push(document.activeElement.id);
                                    }
                                }).observe(dialog, { attributes: true, attributeFilter: ['class'] });
                            }
                        """)

                        page.locator("#add-trigger").click()
                        self.assertTrue(page.locator("#product_id").evaluate("el => document.activeElement === el"))
                        self.assertEqual(page.locator("#addProductModal").get_attribute("aria-hidden"), "false")

                        page.locator("#add-submit").focus()
                        page.keyboard.press("Tab")
                        self.assertTrue(page.locator("#add-close").evaluate("el => document.activeElement === el"))
                        page.keyboard.press("Shift+Tab")
                        self.assertTrue(page.locator("#add-submit").evaluate("el => document.activeElement === el"))

                        page.keyboard.press("Escape")
                        self.assertTrue(page.locator("#add-trigger").evaluate("el => document.activeElement === el"))
                        self.assertEqual(page.locator("#addProductModal").get_attribute("aria-hidden"), "true")
                        self.assertEqual(page.evaluate("window.focusAtDialogHide.at(-1)"), "add-trigger")

                        page.locator("#outside-control").click()
                        page.keyboard.press("Escape")
                        self.assertTrue(page.locator("#outside-control").evaluate("el => document.activeElement === el"))

                        page.locator("#edit-trigger").click()
                        self.assertTrue(page.locator("#new_status").evaluate("el => document.activeElement === el"))
                        page.keyboard.press("Escape")
                        self.assertTrue(page.locator("#edit-trigger").evaluate("el => document.activeElement === el"))
                        self.assertEqual(page.locator("#editStatusModal").get_attribute("aria-hidden"), "true")
                        self.assertEqual(page.evaluate("window.focusAtDialogHide.at(-1)"), "edit-trigger")
                    finally:
                        page.close()
            finally:
                browser.close()

    def test_admin_table_actions_name_their_row_context(self):
        root = Path(settings.BASE_DIR) / "templates" / "admin_panel"
        expectations = {
            "users_list.html": (
                'aria-label="Gestionar productos de {{ user_obj.username }}"',
                'aria-label="Editar usuario {{ user_obj.username }}"',
                'aria-label="Eliminar usuario {{ user_obj.username }}"',
            ),
            "products_list.html": (
                'aria-label="Editar producto {{ product.name }}"',
                'aria-label="Eliminar producto {{ product.name }}"',
            ),
            "contact_requests_list.html": (
                'aria-label="Ver consulta de {{ contact.nombre }}"',
                'aria-label="Eliminar consulta de {{ contact.nombre }}"',
            ),
        }

        for name, labels in expectations.items():
            source = (root / name).read_text(encoding="utf-8")
            for label in labels:
                with self.subTest(template=name, label=label):
                    self.assertIn(label, source)
