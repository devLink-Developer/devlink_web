# Invoice Cancellations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe total and partial cancellation workflows that prepare associated Nota de Crédito C drafts from a customer's authorized invoices while accounting for prior and pending credits.

**Architecture:** Add explicit cancellation metadata and source-line links, centralize balance calculation and draft preparation in `billing/credits.py`, and expose a customer-centered cancellation workspace plus a per-invoice partial flow. Total cancellation creates one exact-balance credit note per selected invoice; partial cancellation preserves original unit prices and source-line quantities. Existing issuance remains the only path that contacts ARCA.

**Tech Stack:** Django 4.2, PostgreSQL/SQLite tests, Django templates/forms, vanilla JavaScript/CSS, ReportLab, existing WSFEv1 client.

**Spec:** `docs/superpowers/specs/2026-11-12-invoice-cancellations-design.md`

## Global Constraints

- A fiscal cancellation is a Nota de Crédito C (`document_type=13`) associated with exactly one authorized Factura C.
- Never delete or mutate an authorized invoice and never emit automatically from the preparation workflow.
- One credit-note draft is created per selected invoice, atomically for a batch.
- `authorized`, `sending`, and `unknown` credit notes consume or reserve balance.
- New credit notes require a reason; historical notes may display “Motivo no registrado”.
- Partial credits use original unit prices and quantities; total credits use one exact-balance summary line.
- Production issuance remains controlled by the existing `BILLING_ALLOW_PRODUCTION` and configuration flags.
- All creation/discard endpoints remain superuser-only, POST-only, and CSRF-protected.

## Review Focus

- Imported invoice with an external credit missing locally: show the local-history warning and require explicit imported-line confirmation for partial preparation.
- Rounding mismatch between remaining source quantities and money: total preparation must use the exact monetary balance, never a recomputed line sum.
- Concurrent preparation or issuance against the same original: row locking must prevent duplicate drafts and over-credit.
- Existing editable or uncertain credit note: offer continuation and do not prepare another.
- Historical credit lines without a unique source-line match: preserve total balance accounting and block automated partial quantities.

---

### Task 1: Persist cancellation intent and line provenance

**Files:**
- Modify: `billing/models.py`
- Create: `billing/migrations/0004_invoice_cancellation_fields.py`
- Modify: `billing/tests/test_models.py`

**Interfaces:**
- Produces: `Invoice.cancellation_kind: str`, `Invoice.cancellation_reason: str`, `InvoiceLine.original_line: InvoiceLine | None`.
- Produces: `InvoiceLine.clean()` validation that a source line belongs to the associated original invoice and cannot be used by a normal invoice.

- [ ] **Step 1: Write failing model tests**

Add tests named `test_credit_line_must_reference_its_original_invoice`, `test_normal_invoice_line_cannot_reference_an_original_line`, and `test_authorized_cancellation_metadata_is_immutable`.

- [ ] **Step 2: Run model tests and verify RED**

Run: `python manage.py test billing.tests.test_models --settings=devlink_web.test_settings --noinput`

Expected: FAIL because the cancellation fields and source-line validation do not exist.

- [ ] **Step 3: Add fields, validation, and migration**

Add `cancellation_kind` choices `total`/`partial`, `cancellation_reason` with maximum 500 characters, and nullable self-FK `original_line` on `InvoiceLine` using `PROTECT` and `related_name='credit_lines'`. The migration should best-effort link pre-existing credit lines only when exactly one original line has the same description and unit price; leave ambiguous rows null.

- [ ] **Step 4: Run model tests and migration checks**

Run: `python manage.py test billing.tests.test_models --settings=devlink_web.test_settings --noinput`

Run: `python manage.py makemigrations --check --dry-run`

Expected: PASS and “No changes detected”.

- [ ] **Step 5: Commit**

```bash
git add billing/models.py billing/migrations/0004_invoice_cancellation_fields.py billing/tests/test_models.py
git commit -m "Add cancellation provenance to billing records"
```

### Task 2: Centralize balances and draft preparation

**Files:**
- Create: `billing/credits.py`
- Create: `billing/tests/test_credits.py`
- Modify: `billing/services.py`
- Modify: `billing/validation.py`

**Interfaces:**
- Produces: immutable `CreditSummary` and `CreditLineSummary` dataclasses.
- Produces: `credit_summary(invoice: Invoice, *, exclude_note_id=None) -> CreditSummary`.
- Produces: `prepare_total_credits(customer_id: int, invoice_ids: list[UUID], reason: str, user) -> list[Invoice]`.
- Produces: `prepare_partial_credit(invoice_id: UUID, quantities: dict[int, Decimal], reason: str, user, *, imported_lines_confirmed: bool=False) -> Invoice`.
- Produces: `discard_credit_draft(invoice_id: UUID, user) -> None`.
- Consumes: Task 1 cancellation fields and original-line links.

- [ ] **Step 1: Write failing balance tests**

Cover no credits, authorized partial credit, pending/unknown reservation, rejected/draft non-reservation, fully cancelled status, unsupported historical unlinked credit lines, and exact remaining monetary balance after rounded partial credits.

- [ ] **Step 2: Run credit tests and verify RED**

Run: `python manage.py test billing.tests.test_credits --settings=devlink_web.test_settings --noinput`

Expected: FAIL because `billing.credits` does not exist.

- [ ] **Step 3: Implement read-only summaries**

Implement dataclasses with original total, authorized amount, reserved amount, available amount, state label, existing editable note, automation-block reason, and per-line original/committed/available quantities. Use `Decimal`, prefetch-friendly query access, and committed states `authorized`, `sending`, `unknown`.

- [ ] **Step 4: Run summary tests and verify GREEN**

Run: `python manage.py test billing.tests.test_credits --settings=devlink_web.test_settings --noinput`

Expected: summary tests PASS.

- [ ] **Step 5: Write failing preparation tests**

Cover multi-select total creating one exact-balance draft per invoice, atomic rollback when any invoice is invalid, mandatory reason, customer ownership, duplicate editable draft, full cancellation, partial quantity bounds, original price preservation, imported partial confirmation, discard restrictions, and non-admin denial.

- [ ] **Step 6: Run preparation tests and verify RED**

Run: `python manage.py test billing.tests.test_credits --settings=devlink_web.test_settings --noinput`

Expected: preparation tests FAIL because functions are missing.

- [ ] **Step 7: Implement preparation under row locks**

Lock the selected customer invoices with `select_for_update()` in deterministic order. Recompute summaries inside the transaction, create total summary lines or partial source-linked lines, and never call `ArcaClient`. Reject an entire batch if any selected invoice is stale or invalid.

- [ ] **Step 8: Harden issuance validation**

Require cancellation metadata for new credit notes, verify associated receiver/emitter, check partial source links and immutable prices, retain the existing total balance guard, and add line-quantity guards under the original invoice lock before WSFE numbering.

- [ ] **Step 9: Run domain and issuance tests**

Run: `python manage.py test billing.tests.test_credits billing.tests.test_services billing.tests.test_models --settings=devlink_web.test_settings --noinput`

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add billing/credits.py billing/services.py billing/validation.py billing/tests/test_credits.py billing/tests/test_services.py
git commit -m "Implement safe invoice cancellation balances"
```

### Task 3: Add cancellation forms, routes, and permission-safe views

**Files:**
- Modify: `billing/forms.py`
- Modify: `billing/views.py`
- Modify: `billing/urls.py`
- Modify: `billing/tests/test_views.py`

**Interfaces:**
- Produces: `CancellationSelectionForm`, `PartialCancellationForm` with dynamic quantity fields from `CreditSummary`.
- Produces routes `billing:cancellations`, `billing:cancellation_partial`, and `billing:credit_discard`.
- Consumes Task 2 summary/preparation/discard functions.

- [ ] **Step 1: Write failing view tests**

Test superuser-only access, CSRF and POST enforcement, customer filtering, disabled fully-cancelled choices, multi-select total preparation, partial validation errors, imported confirmation, stale selection rejection, continuation of an existing draft, and discard restrictions.

- [ ] **Step 2: Run view tests and verify RED**

Run: `python manage.py test billing.tests.test_views --settings=devlink_web.test_settings --noinput`

Expected: FAIL because routes and forms are absent.

- [ ] **Step 3: Implement forms and views**

Parse selected invoice UUIDs only through validated forms, derive customer/invoice/price data server-side, call Task 2 services, use Django messages, and redirect to created drafts or the cancellation workspace. Preserve the old `credit_note` POST route by redirecting to the partial/total choice for that invoice without creating an unsafe free note.

- [ ] **Step 4: Run view tests and verify GREEN**

Run: `python manage.py test billing.tests.test_views --settings=devlink_web.test_settings --noinput`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add billing/forms.py billing/views.py billing/urls.py billing/tests/test_views.py
git commit -m "Add customer cancellation workflows"
```

### Task 4: Build the cancellation workspace and detail presentation

**Files:**
- Create: `templates/billing/cancellations.html`
- Create: `templates/billing/cancellation_partial.html`
- Modify: `templates/billing/base.html`
- Modify: `templates/billing/detail.html`
- Modify: `templates/billing/dashboard.html`
- Modify: `templates/billing/invoice_form.html`
- Modify: `static/billing/billing.css`
- Modify: `static/billing/billing.js`
- Modify: `billing/tests/test_views.py`

**Interfaces:**
- Consumes Task 3 context keys `customers`, `selected_customer`, `invoice_rows`, `selection_form`, `partial_form`, and `credit_summary`.
- Produces keyboard-accessible selection and responsive states without changing server contracts.

- [ ] **Step 1: Add failing template assertions**

Assert navigation exposes “Anulaciones”, fully cancelled invoices remain visible and disabled, partial/total/pending/draft states and balances render, existing drafts have a continuation link, detail pages show related notes and reason, and credit notes cannot be edited through the generic invoice form.

- [ ] **Step 2: Run template/view tests and verify RED**

Run: `python manage.py test billing.tests.test_views --settings=devlink_web.test_settings --noinput`

Expected: FAIL on missing UI text and links.

- [ ] **Step 3: Implement templates and CSS**

Use the existing billing visual language. Add a customer selector, responsive invoice rows, 44px checkbox/action targets, clear monetary columns, a selected-count summary, destructive-action confirmation copy, and explicit local-history warnings for imported invoices.

- [ ] **Step 4: Add progressive enhancement**

Update `billing.js` to maintain selected count/total, enable the batch submit only with a selection and reason, and preserve full server-side behavior without JavaScript.

- [ ] **Step 5: Run view tests and static checks**

Run: `python manage.py test billing.tests.test_views --settings=devlink_web.test_settings --noinput`

Run: `python manage.py collectstatic --noinput --dry-run --settings=devlink_web.test_settings`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add templates/billing static/billing billing/tests/test_views.py
git commit -m "Design invoice cancellation workspace"
```

### Task 5: Include cancellation evidence in fiscal PDF and complete concurrency coverage

**Files:**
- Modify: `billing/pdf.py`
- Modify: `billing/tests/test_views.py`
- Modify: `billing/tests/test_services.py`
- Modify: `billing/tests/test_credits.py`

**Interfaces:**
- Consumes Task 1 metadata and Task 2 balance rules.
- Produces PDF text containing associated invoice, cancellation scope, and escaped reason for new credit notes.

- [ ] **Step 1: Write failing PDF and concurrency tests**

Assert generated credit PDFs include the associated fiscal number, “Anulación total” or “Anulación parcial”, and escaped reason. Add PostgreSQL-only tests for concurrent draft preparation and concurrent partial/total issuance against the same remaining balance.

- [ ] **Step 2: Run tests and verify RED**

Run: `python manage.py test billing.tests.test_views billing.tests.test_services billing.tests.test_credits --settings=devlink_web.test_settings --noinput`

Expected: FAIL on missing PDF evidence and concurrency behavior where applicable.

- [ ] **Step 3: Implement PDF evidence and close race gaps**

Render cancellation metadata only for credit notes; keep historical blank reasons out of fiscal PDFs. Refine row-lock ordering without network calls inside the preparation transactions.

- [ ] **Step 4: Run the complete isolated suite**

Run: `python manage.py test --settings=devlink_web.test_settings --noinput`

Expected: all tests PASS with only explicitly PostgreSQL-gated concurrency tests skipped on SQLite.

- [ ] **Step 5: Run deployment checks**

Run: `python manage.py check --settings=devlink_web.test_settings`

Run: `python manage.py makemigrations --check --dry-run`

Run: `git diff --check`

Expected: no issues, no pending migrations, no whitespace errors.

- [ ] **Step 6: Commit**

```bash
git add billing/pdf.py billing/tests docs/superpowers
git commit -m "Complete auditable invoice cancellation flow"
```

