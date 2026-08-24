"""Reproducible Task 7 visual evidence for database-independent review.

The public and authenticated surfaces use the production Django templates and
stylesheet. Representative context objects stand in for the unavailable remote
PostgreSQL/Mongo data sources; no context value is written into production code.
"""

from __future__ import annotations

import base64
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
FONT_DIR = ROOT / "static" / "fonts"


def capture_css() -> str:
    """Inline self-hosted fonts because set_content has no URL base."""

    css = CSS_TEXT
    for filename in (
        "ibm-plex-sans-regular.woff2",
        "ibm-plex-sans-medium.woff2",
        "ibm-plex-sans-semibold.woff2",
        "ibm-plex-sans-bold.woff2",
    ):
        encoded = base64.b64encode((FONT_DIR / filename).read_bytes()).decode(
            "ascii"
        )
        css = css.replace(
            f'url("fonts/{filename}")',
            f'url("data:font/woff2;base64,{encoded}")',
        )
    return css


CAPTURE_CSS_TEXT = capture_css()


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
                        page.add_style_tag(content=CAPTURE_CSS_TEXT)
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
                            () => {
                                const heading = document.querySelector('h1, h2, h3');
                                const headingStyle = heading
                                    ? getComputedStyle(heading)
                                    : null;
                                const reportRefresh = document.querySelector('.report-refresh');
                                const suiteProducts = document.querySelector('.suite-products');
                                const processSteps = document.querySelector('.process-steps');
                                const reportShell = document.querySelector('.dashboard-shell');
                                const reportScrollers = [...document.querySelectorAll(
                                    '.report-table-wrap'
                                )];
                                const reportNote = document.querySelector('.dashboard-note');
                                const portalPage = document.querySelector('.portal-page');
                                const rect = element => {
                                    if (!element) return null;
                                    const bounds = element.getBoundingClientRect();
                                    return {
                                        left: bounds.left,
                                        right: bounds.right,
                                        width: bounds.width,
                                    };
                                };
                                const reportScrollerMetrics = reportScrollers.map(element => {
                                    const bounds = rect(element);
                                    const scrollLeftBefore = element.scrollLeft;
                                    element.scrollLeft = 80;
                                    const scrollLeftAfter = element.scrollLeft;
                                    element.scrollLeft = 0;
                                    return {
                                        ...bounds,
                                        clientWidth: element.clientWidth,
                                        scrollWidth: element.scrollWidth,
                                        scrollLeftBefore,
                                        scrollLeftAfter,
                                    };
                                });
                                return {
                                    title: document.title,
                                    textLength: document.body.innerText.trim().length,
                                    scrollY: window.scrollY,
                                    bodyWidth: document.body.scrollWidth,
                                    documentWidth: document.documentElement.scrollWidth,
                                    viewportWidth: document.documentElement.clientWidth,
                                    documentHeight: document.documentElement.scrollHeight,
                                    background: getComputedStyle(document.body).backgroundColor,
                                    headingFontFamily: headingStyle?.fontFamily ?? null,
                                    headingFontLoaded: heading
                                        ? document.fonts.check(
                                            `${headingStyle.fontWeight} ${headingStyle.fontSize} "IBM Plex Sans"`,
                                            heading.textContent,
                                        )
                                        : null,
                                    reportRefreshHeight: reportRefresh
                                        ? reportRefresh.getBoundingClientRect().height
                                        : null,
                                    portalOverflowX: portalPage
                                        ? getComputedStyle(portalPage).overflowX
                                        : null,
                                    reportShellRect: rect(reportShell),
                                    reportScrollerMetrics,
                                    reportNoteRect: rect(reportNote),
                                    reportNoteClientWidth: reportNote?.clientWidth ?? null,
                                    reportNoteScrollWidth: reportNote?.scrollWidth ?? null,
                                    reportNoteWhiteSpace: reportNote
                                        ? getComputedStyle(reportNote).whiteSpace
                                        : null,
                                    suiteCollectionTag: suiteProducts?.tagName ?? null,
                                    suiteProductNumberCount: document.querySelectorAll(
                                        '.suite-product-number'
                                    ).length,
                                    processCollectionTag: processSteps?.tagName ?? null,
                                    processItemCount: processSteps?.children.length ?? null,
                                    processListStyleType: processSteps
                                        ? getComputedStyle(processSteps).listStyleType
                                        : null,
                                    processPaddingInlineStart: processSteps
                                        ? getComputedStyle(processSteps).paddingInlineStart
                                        : null,
                                    processCustomMarkerCount: processSteps
                                        ? [...processSteps.children].filter(item => {
                                            const content = getComputedStyle(
                                                item,
                                                '::before'
                                            ).content;
                                            return content !== 'none'
                                                && content.includes('counter(step)');
                                        }).length
                                        : null,
                                };
                            }
                            """
                        )
                        if measurements["scrollY"] != 0:
                            raise RuntimeError(f"{surface['slug']} did not start at top")
                        if measurements["textLength"] < 80:
                            raise RuntimeError(f"{surface['slug']} rendered as blank/wrong surface")
                        if measurements["background"] in {"rgb(0, 0, 0)", "#000000"}:
                            raise RuntimeError(f"{surface['slug']} rendered with black body")
                        if not measurements["headingFontFamily"].startswith(
                            '"IBM Plex Sans"'
                        ):
                            raise RuntimeError(
                                f"{surface['slug']} did not compute IBM Plex Sans"
                            )
                        if not measurements["headingFontLoaded"]:
                            raise RuntimeError(
                                f"{surface['slug']} did not load IBM Plex Sans"
                            )
                        if measurements["documentWidth"] != measurements["viewportWidth"]:
                            raise RuntimeError(
                                f"{surface['slug']} has page-level horizontal overflow"
                            )
                        if console_errors:
                            raise RuntimeError(
                                f"{surface['slug']} logged console errors: {console_errors}"
                            )
                        if (
                            surface["slug"] == "client-report"
                            and size_name == "mobile"
                            and measurements["reportRefreshHeight"] > 96
                        ):
                            raise RuntimeError(
                                "client-report mobile refresh panel exceeds 96px"
                            )
                        if surface["slug"] == "client-report":
                            shell = measurements["reportShellRect"]
                            scrollers = measurements["reportScrollerMetrics"]
                            note = measurements["reportNoteRect"]
                            if measurements["portalOverflowX"] != "visible":
                                raise RuntimeError(
                                    "client-report still masks horizontal overflow"
                                )
                            if shell["left"] < 0 or shell["right"] > viewport["width"]:
                                raise RuntimeError(
                                    "client-report shell exceeds viewport bounds"
                                )
                            if note["right"] > viewport["width"]:
                                raise RuntimeError(
                                    "client-report footer note exceeds viewport bounds"
                                )
                            if (
                                measurements["reportNoteScrollWidth"]
                                > measurements["reportNoteClientWidth"] + 1
                                or measurements["reportNoteWhiteSpace"] != "normal"
                            ):
                                raise RuntimeError(
                                    "client-report footer note does not wrap"
                                )
                            if size_name == "mobile":
                                if len(scrollers) != 2 or any(
                                    scroller["left"] < 0
                                    or scroller["right"] > viewport["width"]
                                    or scroller["scrollWidth"]
                                    <= scroller["clientWidth"]
                                    or scroller["scrollLeftBefore"] != 0
                                    or scroller["scrollLeftAfter"] <= 0
                                    for scroller in scrollers
                                ):
                                    raise RuntimeError(
                                        "client-report mobile table scroll is not contained/operable"
                                    )
                            elif (
                                abs(shell["width"] - 1180) > 1
                                or any(
                                    scroller["scrollWidth"] != scroller["clientWidth"]
                                    for scroller in scrollers
                                )
                            ):
                                raise RuntimeError(
                                    "client-report desktop geometry changed"
                                )
                        if surface["slug"] == "homepage" and (
                            measurements["suiteCollectionTag"] != "UL"
                            or measurements["suiteProductNumberCount"] != 0
                        ):
                            raise RuntimeError(
                                "homepage Suite Lite semantics/numbers regressed"
                            )
                        if surface["slug"] == "homepage" and (
                            measurements["processCollectionTag"] != "OL"
                            or measurements["processItemCount"] != 4
                            or measurements["processListStyleType"] != "none"
                            or measurements["processPaddingInlineStart"] != "0px"
                            or measurements["processCustomMarkerCount"] != 4
                        ):
                            raise RuntimeError(
                                "homepage methodology marker semantics regressed"
                            )

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
