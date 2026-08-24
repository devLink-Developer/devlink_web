# DevLink Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar todas las superficies públicas y autenticadas de devLink con una identidad SaaS tecnológica coherente, conservando contenido, rutas y comportamiento.

**Architecture:** Mantener Django server-rendered y consolidar el sistema visual en `static/styles.css`, con `templates/base.html` como base de las superficies autenticadas. Las plantillas públicas conservarán su estructura funcional y adoptarán el mismo sistema mediante clases semánticas; no se añadirá un framework JavaScript ni una librería de componentes.

**Tech Stack:** Django templates, HTML5, CSS custom properties, JavaScript nativo, Django TestCase.

**Spec:** `docs/superpowers/specs/2026-08-23-devlink-frontend-redesign-design.md`

## Global Constraints

- Conservar contenido visible, rutas, anclas, nombres de navegación, campos, variables Django y comportamiento.
- Tema claro único con blanco dominante, `#07162d`, `#1264f6` y `#06d6ff`.
- `DESIGN_VARIANCE: 6`, `MOTION_INTENSITY: 4`, `VISUAL_DENSITY: 5`.
- Contraste WCAG AA, foco visible, navegación por teclado y `prefers-reduced-motion`.
- No añadir métricas, testimonios, clientes, capacidades ni capturas de producto ficticias.
- No modificar backend, modelos, permisos, integraciones ni URLs.
- Preservar los archivos no relacionados que ya están sin seguimiento en el worktree.

---

### Task 1: Sistema visual compartido y contrato de dirección

**Files:**
- Modify: `static/styles.css`
- Modify: `templates/base.html`
- Create: `accounts/tests_frontend.py`

**Interfaces:**
- Consumes: variables de plantillas Django y bloques `{% block title %}` / `{% block content %}` existentes.
- Produces: tokens `--brand-*`, `--surface-*`, `--text-*`, `--radius-*`; componentes `.app-shell`, `.app-header`, `.page-shell`, `.panel`, `.button`, `.field`, `.data-table`, `.alert`.

- [ ] **Step 1: Escribir pruebas de contrato frontend**

```python
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase


class FrontendContractTests(SimpleTestCase):
    def test_base_loads_shared_styles_and_brand(self):
        source = (Path(settings.BASE_DIR) / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("{% load static %}", source)
        self.assertIn("{% static 'styles.css' %}", source)
        self.assertIn("DevLink", source)

    def test_styles_expose_brand_and_accessibility_tokens(self):
        css = (Path(settings.BASE_DIR) / "static" / "styles.css").read_text(encoding="utf-8")
        for token in ("--brand-900", "--brand-600", "--accent-500", "--focus-ring"):
            self.assertIn(token, css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn(":focus-visible", css)
```

- [ ] **Step 2: Ejecutar pruebas y confirmar el fallo inicial**

Run: `python manage.py test accounts.tests_frontend -v 2`

Expected: FAIL porque `base.html` todavía no carga `styles.css` y faltan tokens/componentes nuevos.

- [ ] **Step 3: Implementar base, tokens y componentes**

```html
{% load static %}
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}DevLink - Portal Cliente{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'styles.css' %}">
</head>
<body class="app-body">
  <!-- THESIS / OWN-WORLD / STORY / FIRST VIEWPORT / FORM / FINISH contract -->
  <div id="toast-container" class="toast-region" aria-live="polite"></div>
  {% block content %}{% endblock %}
</body>
</html>
```

Implementar en CSS los tokens aprobados, reset, tipografía, botones, formularios, alertas, tablas, paneles, navegación, estados, responsive y movimiento reducido.

- [ ] **Step 4: Ejecutar pruebas del contrato**

Run: `python manage.py test accounts.tests_frontend -v 2`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add static/styles.css templates/base.html accounts/tests_frontend.py
git commit -m "feat: establish devlink frontend design system"
```

### Task 2: Página pública y navegación comercial

**Files:**
- Modify: `templates/index.html`
- Modify: `static/styles.css`
- Test: `accounts/tests_frontend.py`

**Interfaces:**
- Consumes: tokens y componentes de Task 1; formulario `POST /` con `nombre`, `email`, `empresa`, `proyecto`, `newsletter`.
- Produces: `.marketing-page`, `.site-header`, `.hero`, `.capability-map`, `.service-grid`, `.suite-products`, `.process-steps`, `.contact-grid`.

- [ ] **Step 1: Añadir prueba de preservación de contenido y estructura**

```python
    def test_home_preserves_sections_and_contact_fields(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for section_id in ("inicio", "servicios", "suite-lite", "soluciones", "metodologia", "contacto"):
            self.assertContains(response, f'id="{section_id}"')
        for field in ("nombre", "email", "empresa", "proyecto", "newsletter"):
            self.assertContains(response, f'name="{field}"')
```

- [ ] **Step 2: Confirmar que la prueba actual pasa antes de recomponer**

Run: `python manage.py test accounts.tests_frontend.FrontendContractTests.test_home_preserves_sections_and_contact_fields -v 2`

Expected: PASS; esta prueba protege el contenido funcional durante el rediseño.

- [ ] **Step 3: Recomponer el marketing completo**

Mantener cada texto y enlace existente, aplicar el contrato visual como primer comentario de `<body>`, convertir el hero en split asimétrico, dar ritmos distintos a métricas, servicios, Suite Lite, soluciones, metodología, CTA y contacto, y conservar el menú móvil accesible.

Cambiar el `<body>` a `class="marketing-page"`; añadir `section-shell` a hero, prueba, servicios, Suite Lite, soluciones, metodología y contacto; y conservar `site-header`, `data-header`, `data-nav-toggle`, `data-nav` y todos los IDs actuales.

- [ ] **Step 4: Ejecutar pruebas y validación Django**

Run: `python manage.py test accounts.tests_frontend -v 2 && python manage.py check`

Expected: PASS y `System check identified no issues`.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/styles.css accounts/tests_frontend.py
git commit -m "feat: redesign devlink marketing site"
```

### Task 3: Login, documentación y páginas legales

**Files:**
- Modify: `templates/accounts/login.html`
- Modify: `templates/documentacion.html`
- Modify: `templates/politicas-privacidad.html`
- Modify: `templates/terminos-servicio.html`
- Modify: `templates/aviso-iluminacion.html`
- Modify: `static/styles.css`
- Test: `accounts/tests_frontend.py`

**Interfaces:**
- Consumes: formulario de login `username` / `password`, rutas y anclas legales/documentales existentes.
- Produces: `.auth-layout`, `.auth-panel`, `.docs-layout`, `.docs-sidebar`, `.article-shell`, `.legal-layout`.

- [ ] **Step 1: Añadir pruebas de rutas, campos y hoja compartida**

```python
    def test_public_reading_surfaces_use_shared_styles(self):
        for route in ("/politicas-privacidad/", "/terminos-servicio/", "/aviso-iluminacion/"):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "styles.css")

    def test_login_keeps_authentication_fields(self):
        response = self.client.get("/portal/")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, "csrfmiddlewaretoken")
```

- [ ] **Step 2: Ejecutar pruebas de preservación**

Run: `python manage.py test accounts.tests_frontend -v 2`

Expected: PASS antes y después del cambio.

- [ ] **Step 3: Aplicar layouts de autenticación y lectura**

En login, envolver el contenido existente en `main.auth-layout`, usar `section.auth-intro[aria-labelledby="portal-title"]` para la introducción y `section.auth-panel` para el formulario. En documentación y legales, aplicar `main.reading-layout`, `aside.reading-sidebar` y `article.article-shell` sin cambiar IDs ni texto.

Mantener el contenido legal intacto, añadir contenedores de lectura, índices laterales accesibles, estados activos y colapso móvil explícito.

- [ ] **Step 4: Verificar rutas y HTML renderizado**

Run: `python manage.py test accounts.tests_frontend -v 2 && python manage.py check`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/accounts/login.html templates/documentacion.html templates/politicas-privacidad.html templates/terminos-servicio.html templates/aviso-iluminacion.html static/styles.css accounts/tests_frontend.py
git commit -m "feat: redesign auth docs and legal surfaces"
```

### Task 4: Portal cliente y dashboards

**Files:**
- Modify: `templates/dashboard/main.html`
- Modify: `templates/dashboard/whatsapp_report.html`
- Modify: `templates/dashboard/edit_questions.html`
- Modify: `static/styles.css`
- Test: `accounts/tests_frontend.py`

**Interfaces:**
- Consumes: `user`, `tenant_id`, `client_products`, `website_url`, `page_obj`, métricas y formularios de edición existentes.
- Produces: `.app-header`, `.dashboard-shell`, `.metric-grid`, `.product-list`, `.report-table`, `.editor-list`.

- [ ] **Step 1: Añadir pruebas estáticas que protejan variables y acciones críticas**

```python
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
                self.assertIn(needle, source)
```

- [ ] **Step 2: Ejecutar la prueba de bindings**

Run: `python manage.py test accounts.tests_frontend.FrontendContractTests.test_dashboard_templates_keep_critical_bindings -v 2`

Expected: PASS.

- [ ] **Step 3: Aplicar shell y componentes operativos**

Aplicar `div.app-shell` como raíz, `header.app-header` a la cabecera existente, `main.dashboard-shell` al contenido, `div.page-heading` al título/acciones, `section.metric-grid` a métricas y `section.panel` a cada grupo operativo.

Preservar bucles, condiciones, formularios, paginación y JavaScript. Sustituir estilos inline por clases del sistema cuando sea seguro.

- [ ] **Step 4: Ejecutar suite y check**

Run: `python manage.py test accounts.tests_frontend -v 2 && python manage.py check`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/dashboard static/styles.css accounts/tests_frontend.py
git commit -m "feat: redesign client portal dashboards"
```

### Task 5: Panel administrativo completo

**Files:**
- Modify: `templates/admin_panel/*.html`
- Modify: `static/styles.css`
- Test: `accounts/tests_frontend.py`

**Interfaces:**
- Consumes: variables, URLs, formularios y acciones existentes en las 12 plantillas administrativas.
- Produces: variantes `.admin-shell`, `.admin-toolbar`, `.data-table`, `.form-grid`, `.danger-panel`, `.status-badge`.

- [ ] **Step 1: Añadir prueba de cobertura de plantillas administrativas**

```python
    def test_admin_templates_extend_shared_base_and_keep_csrf(self):
        root = Path(settings.BASE_DIR) / "templates" / "admin_panel"
        templates = list(root.glob("*.html"))
        self.assertGreaterEqual(len(templates), 12)
        for path in templates:
            source = path.read_text(encoding="utf-8")
            self.assertIn("{% extends 'base.html' %}", source)
        for name in ("user_form.html", "user_edit.html", "product_form.html", "product_edit.html", "user_confirm_delete.html"):
            self.assertIn("{% csrf_token %}", (root / name).read_text(encoding="utf-8"))
```

- [ ] **Step 2: Ejecutar prueba de cobertura**

Run: `python manage.py test accounts.tests_frontend.FrontendContractTests.test_admin_templates_extend_shared_base_and_keep_csrf -v 2`

Expected: PASS.

- [ ] **Step 3: Rediseñar navegación, tablas, formularios y detalles**

Aplicar `div.admin-shell.page-shell` como raíz de cada contenido administrativo, `div.admin-toolbar` a títulos y acciones, `section.panel.panel--data` a tablas/detalles, `form.form-grid` a formularios y `section.danger-panel` a confirmaciones destructivas.

Mantener acciones destructivas visualmente diferenciadas, nombres de campo, URLs y confirmaciones. Hacer explícito el fallback móvil de tablas y toolbars.

- [ ] **Step 4: Ejecutar suite y check**

Run: `python manage.py test accounts.tests_frontend -v 2 && python manage.py check`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/admin_panel static/styles.css accounts/tests_frontend.py
git commit -m "feat: redesign administration interface"
```

### Task 6: Plantillas de correo y previsualizaciones

**Files:**
- Modify: `templates/email-bienvenida.html`
- Modify: `templates/email-preview.html`
- Modify: `templates/email-campana-servicios-inline.html`
- Modify: `templates/email-campana-suite-lite-inline.html`
- Modify: `templates/email-campana-chatbot-webapp.html`
- Test: `accounts/tests_frontend.py`

**Interfaces:**
- Consumes: texto, enlaces, CTA y restricciones de compatibilidad de correo existentes.
- Produces: versión inline del sistema de marca con fondo blanco, cabecera azul marino, CTA azul y detalles cian.

- [ ] **Step 1: Añadir prueba de preservación de enlaces y paleta**

```python
    def test_email_templates_keep_brand_and_contact_links(self):
        root = Path(settings.BASE_DIR) / "templates"
        for name in ("email-bienvenida.html", "email-preview.html", "email-campana-servicios-inline.html", "email-campana-suite-lite-inline.html", "email-campana-chatbot-webapp.html"):
            source = (root / name).read_text(encoding="utf-8")
            self.assertIn("devLink", source)
            self.assertIn("devlink.com.ar", source)
            self.assertRegex(source.lower(), r"#(?:07162d|1264f6|06d6ff)")
```

- [ ] **Step 2: Ejecutar prueba y observar plantillas que aún no cumplen la paleta unificada**

Run: `python manage.py test accounts.tests_frontend.FrontendContractTests.test_email_templates_keep_brand_and_contact_links -v 2`

Expected: FAIL en cualquier plantilla sin un token de la paleta aprobada.

- [ ] **Step 3: Reestilizar sin alterar contenido ni estructura de correo**

```html
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f8fc;">
  <tr><td align="center">
    <table role="presentation" width="600" style="background:#ffffff;border:1px solid #dbe7f3;border-radius:16px;">
      <!-- contenido existente preservado -->
    </table>
  </td></tr>
</table>
```

Mantener estilos inline, tablas de presentación, enlaces y CTA existentes.

- [ ] **Step 4: Ejecutar pruebas**

Run: `python manage.py test accounts.tests_frontend -v 2`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/email-*.html accounts/tests_frontend.py
git commit -m "feat: align email templates with devlink brand"
```

### Task 7: Verificación visual, detector y documentación del sistema

**Files:**
- Create: `.impeccable/review/desktop.png`
- Create: `.impeccable/review/mobile.png`
- Create: `DESIGN.md`
- Modify: archivos que fallen una comprobación mecánica o visual.

**Interfaces:**
- Consumes: todas las superficies de Tasks 1-6 y el contrato visual.
- Produces: evidencia desktop/mobile, reporte del detector, veredicto independiente y sistema documentado.

- [ ] **Step 1: Ejecutar verificación funcional completa**

Run: `python manage.py test -v 2`

Expected: PASS.

Run: `python manage.py check`

Expected: `System check identified no issues`.

- [ ] **Step 2: Levantar el servidor y capturar desktop/mobile**

Run: `python manage.py runserver 127.0.0.1:8000`

Capturar `/`, `/portal/` y las superficies autenticadas disponibles en 1440 px y 390 px; guardar las capturas representativas en `.impeccable/review/desktop.png` y `.impeccable/review/mobile.png`.

- [ ] **Step 3: Ejecutar detector una sola vez**

Run: `node C:\Users\edespinoza\.codex\skills\impeccable\scripts\detect.mjs --json templates static/styles.css`

Expected: JSON sin fallos mecánicos no resueltos.

- [ ] **Step 4: Ejecutar revisión final independiente y aplicar una tanda de correcciones si corresponde**

Entregar al reviewer la solicitud original, spec, contrato, targets, capturas, findings y `reference/craft-floor.md`; actuar según `ship`, `fix`, `rebuild` o `recapture`.

- [ ] **Step 5: Documentar el sistema construido**

Crear `DESIGN.md` desde el resultado real con tokens, tipografía, radios, componentes, layout, motion, responsive y accesibilidad.

- [ ] **Step 6: Commit final**

```bash
git add templates static accounts/tests_frontend.py DESIGN.md .impeccable/review
git commit -m "feat: complete devlink frontend redesign"
```
