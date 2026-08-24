"""Reproducible Task 7 visual evidence for database-independent review.

The public and authenticated surfaces use the production Django templates and
stylesheet. Representative context objects stand in for the unavailable remote
PostgreSQL/Mongo data sources; no context value is written into production code.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "devlink_web.settings")

import django

django.setup()

from django.contrib.auth.models import AnonymousUser
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import RequestFactory
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


OUTPUT = ROOT / ".impeccable" / "review"
CSS_PATH = ROOT / "static" / "styles.css"
CSS_TEXT = CSS_PATH.read_text(encoding="utf-8-sig")


@dataclass
class Product:
    name: str
    product_type: str
    description: str

    def get_product_type_display(self) -> str:
        return {
            "chatbot": "Chatbot WhatsApp",
            "automation": "Automatización",
        }.get(self.product_type, self.product_type)


@dataclass
class ClientProduct:
    product: Product
    status: str
    start_date: date
    monthly_cost: int

    def get_status_display(self) -> str:
        return {
            "active": "Activo",
            "development": "En desarrollo",
            "suspended": "Suspendido",
        }[self.status]


class ProductCollection:
    def __init__(self, count: int) -> None:
        self._count = count

    def count(self) -> int:
        return self._count


def user(
    username: str,
    company: str,
    email: str,
    tenant: str,
    *,
    user_id: int,
    products: int = 2,
    active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        username=username,
        first_name=username.split(".")[0].title(),
        company_name=company,
        email=email,
        tenant_id=tenant,
        is_active=active,
        is_authenticated=True,
        date_joined=datetime(2026, 7, 18, 10, 30),
        clientprofile=SimpleNamespace(products=ProductCollection(products)),
    )


CLIENT = user(
    "operaciones.demo",
    "Logística Regional",
    "operaciones@empresa.com.ar",
    "tenant-devlink-001",
    user_id=11,
)
ADMIN = user(
    "admin.devlink",
    "devLink",
    "admin@devlink.com.ar",
    "tenant-admin-001",
    user_id=1,
    products=4,
)


def request_for(path: str, current_user: object) -> object:
    request = RequestFactory().get(path)
    request.user = current_user
    return request


def render(template: str, context: dict, path: str, current_user: object) -> str:
    html = render_to_string(
        template,
        context,
        request=request_for(path, current_user),
    )
    # Chrome receives the shared stylesheet directly from disk below. Removing
    # this unresolved root-relative request avoids a false console failure.
    return re.sub(
        r'<link\s+rel="stylesheet"\s+href="/static/styles\.css"\s*/?>',
        "",
        html,
        count=1,
    )


def surfaces() -> list[dict]:
    questions = [
        {
            "pregunta": "¿Cuál es el estado de mi pedido?",
            "total_consultas": 84,
            "usuarios_unicos": 37,
            "ultima_consulta": "23/08/2026 18:42",
        },
        {
            "pregunta": "¿Cuáles son los horarios de atención?",
            "total_consultas": 58,
            "usuarios_unicos": 31,
            "ultima_consulta": "23/08/2026 17:10",
        },
        {
            "pregunta": "Necesito hablar con una persona",
            "total_consultas": 43,
            "usuarios_unicos": 29,
            "ultima_consulta": "23/08/2026 16:25",
        },
    ]
    page_obj = Paginator(questions, 2).page(1)
    client_products = [
        ClientProduct(
            Product(
                "Asistente WhatsApp",
                "chatbot",
                "Atención automatizada y respuestas administrables para clientes.",
            ),
            "active",
            date(2026, 2, 1),
            145000,
        ),
        ClientProduct(
            Product(
                "Sincronización operativa",
                "automation",
                "Flujos de integración para reducir tareas manuales repetitivas.",
            ),
            "development",
            date(2026, 6, 15),
            98000,
        ),
    ]
    editor_menus = [
        {
            "id": "menu-principal",
            "menu": "Menú principal",
            "submenu": "Opciones iniciales del asistente",
            "respuestas": [
                {
                    "id": "respuesta-1",
                    "opcion": "1",
                    "descripcion": "Estado del pedido",
                    "respuesta": "Indícanos tu número de pedido para consultar el estado.",
                },
                {
                    "id": "respuesta-2",
                    "opcion": "2",
                    "descripcion": "Horarios",
                    "respuesta": "Nuestro horario de atención es de lunes a viernes.",
                },
            ],
        },
        {
            "id": "derivacion",
            "menu": "Derivación",
            "submenu": "Escalamiento a atención personalizada",
            "respuestas": [
                {
                    "id": "respuesta-3",
                    "opcion": "1",
                    "descripcion": "Hablar con una persona",
                    "respuesta": "Vamos a derivar tu consulta al equipo de atención.",
                }
            ],
        },
    ]
    managed_users = [
        CLIENT,
        user(
            "comercial.norte",
            "Distribuidora Norte",
            "contacto@distribuidoranorte.com.ar",
            "tenant-devlink-002",
            user_id=12,
            products=1,
        ),
        user(
            "soporte.patagonia",
            "Servicios Patagonia",
            "soporte@patagonia.com.ar",
            "tenant-devlink-003",
            user_id=13,
            products=0,
            active=False,
        ),
    ]

    return [
        {
            "slug": "homepage",
            "template": "index.html",
            "path": "/",
            "user": AnonymousUser(),
            "context": {},
        },
        {
            "slug": "login",
            "template": "accounts/login.html",
            "path": "/portal/",
            "user": AnonymousUser(),
            "context": {},
        },
        {
            "slug": "docs",
            "template": "documentacion.html",
            "path": "/documentacion/",
            "user": CLIENT,
            "context": {},
        },
        {
            "slug": "client-dashboard",
            "template": "dashboard/main.html",
            "path": "/dashboard/",
            "user": CLIENT,
            "context": {
                "user": CLIENT,
                "tenant_id": CLIENT.tenant_id,
                "client_products": client_products,
                "website_url": "https://empresa.com.ar",
            },
        },
        {
            "slug": "client-report",
            "template": "dashboard/whatsapp_report.html",
            "path": "/dashboard/whatsapp-report/",
            "user": CLIENT,
            "context": {
                "user": CLIENT,
                "fecha_reporte": "24/08/2026 02:15",
                "total_consultas": 185,
                "total_preguntas": 36,
                "total_usuarios_unicos": 91,
                "promedio_usuario": "2,03",
                "top_10": questions,
                "page_obj": page_obj,
            },
        },
        {
            "slug": "client-editor",
            "template": "dashboard/edit_questions.html",
            "path": "/dashboard/edit-questions/",
            "user": CLIENT,
            "context": {
                "user": CLIENT,
                "menus": editor_menus,
                "fecha_actual": "24/08/2026 02:15",
            },
        },
        {
            "slug": "admin-dashboard",
            "template": "admin_panel/dashboard.html",
            "path": "/admin-panel/",
            "user": ADMIN,
            "context": {
                "user": ADMIN,
                "total_users": 18,
                "active_users": 16,
                "total_products": 7,
                "active_products": 6,
                "total_contacts": 42,
                "pending_contacts": 4,
                "recent_users": managed_users,
            },
        },
        {
            "slug": "admin-users-list",
            "template": "admin_panel/users_list.html",
            "path": "/admin-panel/users/",
            "user": ADMIN,
            "context": {
                "user": ADMIN,
                "users": managed_users,
                "search_query": "",
            },
        },
        {
            "slug": "admin-user-form",
            "template": "admin_panel/user_form.html",
            "path": "/admin-panel/users/create/",
            "user": ADMIN,
            "context": {"user": ADMIN},
        },
    ]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    review_manifest: list[dict] = []
    manifest_path = OUTPUT / "capture-manifest.json"

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            browser_engine = "installed Chrome"
        except PlaywrightError:
            browser = playwright.chromium.launch(headless=True)
            browser_engine = "Playwright Chromium"

        try:
            for surface in surfaces():
                html = render(
                    surface["template"],
                    surface["context"],
                    surface["path"],
                    surface["user"],
                )
                for size_name, viewport in (
                    ("desktop", {"width": 1440, "height": 900}),
                    ("mobile", {"width": 390, "height": 844}),
                ):
                    context = browser.new_context(
                        viewport=viewport,
                        reduced_motion="reduce",
                        color_scheme="light",
                        locale="es-AR",
                    )
                    page = context.new_page()
                    console_errors: list[str] = []
                    page.on(
                        "console",
                        lambda message: console_errors.append(message.text)
                        if message.type == "error"
                        else None,
                    )
                    try:
                        page.set_content(html, wait_until="domcontentloaded")
                        # styles.css carries a UTF-8 BOM for legacy Windows
                        # compatibility. Decode it here so :root remains a valid
                        # inline selector and every design token resolves.
                        page.add_style_tag(content=CSS_TEXT)
                        page.add_style_tag(
                            content="""
                                *, *::before, *::after {
                                    animation: none !important;
                                    transition: none !important;
                                    scroll-behavior: auto !important;
                                }
                            """
                        )
                        page.evaluate("document.fonts.ready")
                        page.wait_for_timeout(350)
                        page.evaluate("window.scrollTo(0, 0)")
                        page.wait_for_timeout(50)

                        measurements = page.evaluate(
                            """
                            () => ({
                                title: document.title,
                                textLength: document.body.innerText.trim().length,
                                scrollY: window.scrollY,
                                bodyWidth: document.body.scrollWidth,
                                documentWidth: document.documentElement.scrollWidth,
                                viewportWidth: document.documentElement.clientWidth,
                                documentHeight: document.documentElement.scrollHeight,
                                background: getComputedStyle(document.body).backgroundColor,
                            })
                            """
                        )
                        if measurements["scrollY"] != 0:
                            raise RuntimeError(f"{surface['slug']} did not start at top")
                        if measurements["textLength"] < 80:
                            raise RuntimeError(f"{surface['slug']} rendered as blank/wrong surface")
                        if measurements["background"] in {"rgb(0, 0, 0)", "#000000"}:
                            raise RuntimeError(f"{surface['slug']} rendered with black body")

                        path = OUTPUT / f"{surface['slug']}-{size_name}.png"
                        page.screenshot(path=str(path), full_page=True)
                        if surface["slug"] == "homepage":
                            page.screenshot(
                                path=str(OUTPUT / f"{size_name}.png"),
                                full_page=True,
                            )

                        review_manifest.append(
                            {
                                "surface": surface["slug"],
                                "template": surface["template"],
                                "route": surface["path"],
                                "viewport": viewport,
                                "capture": path.name,
                                "browser": browser_engine,
                                "renderMode": "Django template with controlled context",
                                "horizontalOverflowPx": max(
                                    0,
                                    measurements["documentWidth"]
                                    - measurements["viewportWidth"],
                                ),
                                "consoleErrors": console_errors,
                                **measurements,
                            }
                        )
                        manifest_path.write_text(
                            json.dumps(review_manifest, ensure_ascii=False, indent=2)
                            + "\n",
                            encoding="utf-8",
                        )
                        print(f"captured {surface['slug']} {size_name}", flush=True)
                    finally:
                        context.close()
        finally:
            browser.close()

    manifest_path.write_text(
        json.dumps(review_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(review_manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
