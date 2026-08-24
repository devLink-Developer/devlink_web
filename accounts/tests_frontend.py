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
    def test_email_templates_keep_brand_and_contact_links(self):
        root = Path(settings.BASE_DIR) / "templates"
        for name in (
            "email-bienvenida.html",
            "email-preview.html",
            "email-campana-servicios-inline.html",
            "email-campana-suite-lite-inline.html",
            "email-campana-chatbot-webapp.html",
        ):
            source = (root / name).read_text(encoding="utf-8")
            self.assertIn("devLink", source)
            self.assertIn("devlink.com.ar", source)
            self.assertRegex(source.lower(), r"#(?:07162d|1264f6|06d6ff)")

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
