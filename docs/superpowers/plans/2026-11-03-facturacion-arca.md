# Facturación ARCA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Facturación interna de devLink con factura C, nota de crédito C, PDF y conciliación segura.
**Architecture:** Aplicación Django `billing`, modelos propios, adaptador SOAP WSAA/WSFE y coordinación transaccional en PostgreSQL. Plantillas de servidor bajo `/admin-panel/billing/`.
**Tech Stack:** Python 3.11, Django 4.2, PostgreSQL 15, cryptography, requests, defusedxml, ReportLab.
**Spec:** `docs/superpowers/specs/2026-11-03-facturacion-arca-design.md`.

## Global Constraints

- Solo facturación propia, superusuarios; factura C (11) y nota de crédito C (13); moneda PES.
- Certificados privados fuera de Git y MEDIA_ROOT; endpoints oficiales por ambiente; TLS validado.
- Emisión deshabilitada inicialmente; pruebas sin emitir comprobantes reales.
- Persistir estado antes del envío; ningún reintento automático de autorizaciones inciertas.
- Conservar los cambios previos del usuario.

## Review Focus

- POST repetido/concurrente: un único envío fiscal y ninguna reserva perdida.
- Timeout, respuesta parcial o reinicio: estado recuperable, bloqueo de serie y conciliación de identidad completa.
- Notas de crédito concurrentes: no acreditar más del saldo original.
- Edición después de autorizar: snapshots, líneas y configuración histórica inmutables.
- Archivos/PFX, tickets y XML: sin exposición pública, XXE, destinos arbitrarios ni secretos en auditoría.

### Task 1: Datos y validación fiscal

**Files:** `billing/models.py`, `billing/validation.py`, migraciones, `billing/tests/test_models.py`, `devlink_web/test_settings.py`.
**Interfaces:** `Issuer`, `ArcaConfiguration`, `Customer`, `Invoice`, `InvoiceLine`, `InvoiceAttempt`, `AccessTicket`; `validate_invoice(invoice)` y `invoice_payload(invoice)`.
- [x] Crear pruebas de montos/fechas, C sin IVA, nota asociada y archivos privados; ejecutarlas y observar fallo por módulo ausente.
- [x] Implementar modelos, validación y migraciones; correr pruebas hasta verde.

### Task 2: ARCA y coordinación de emisión

**Files:** `billing/arca.py`, `billing/services.py`, `billing/tests/test_arca.py`, `billing/tests/test_services.py`.
**Interfaces:** `ArcaClient(config).last_number(type)`, `.authorize(payload)`, `.consult(type, number)`, `.points_of_sale()`, `.status()`; `issue_invoice(id, user)`, `reconcile_invoice(id, user)`.
- [x] Probar rechazo, aprobación, respuesta incompleta, bloqueo de serie, idempotencia y recuperación; observar rojo.
- [x] Implementar SOAP seguro, certificado/clave/PFX, cache de tickets, reserva persistente y conciliación; correr pruebas incluidas las de concurrencia PostgreSQL.

### Task 3: Interfaz y PDF

**Files:** `billing/forms.py`, `views.py`, `urls.py`, `pdf.py`, `templates/billing/*`, `static/billing/*`, integración de navegación y `billing/tests/test_views.py`.
**Interfaces:** vistas superusuario para configuración, clientes, borradores, emisión, conciliación y PDF.
- [x] Probar acceso, CSRF, cambio de estado, edición inmutable y PDF; observar rojo.
- [x] Implementar formularios y formsets con cálculo servidor, vistas POST y plantillas responsive; verificar suite y PDF renderizado.

### Task 4: Operación y entrega

**Files:** comandos `billing_check` y `billing_reconcile`, `docs/billing.md`, variables de entorno de ejemplo y compose de pruebas/certificados.
- [x] Probar que la configuración inicial no emite; documentar y comprobar migraciones/checks.
- [x] Correr suite completa contra PostgreSQL aislado y revisar interfaz en navegador.
- [x] Revisión independiente del cambio completo y correcciones necesarias; registrar resultados y pendientes de activación.

## Ejecución

Autorizada por el usuario al aprobar el diseño. Implementación continua en esta sesión; no requiere elegir otro método ni una segunda aprobación de este plan. No se hacen commits/push/deploy automáticamente; la entrega queda revisable en la rama `codex/facturacion-arca`.
