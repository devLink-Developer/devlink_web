from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import EDITABLE_STATES, Invoice, InvoiceLine


COMMITTED_CREDIT_STATES = ('authorized', 'sending', 'unknown')
RESERVED_CREDIT_STATES = ('sending', 'unknown')
ZERO = Decimal('0.00')


@dataclass(frozen=True)
class CreditLineSummary:
    line: InvoiceLine
    original_quantity: Decimal
    authorized_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal


@dataclass(frozen=True)
class CreditSummary:
    invoice: Invoice
    original_total: Decimal
    authorized_amount: Decimal
    reserved_amount: Decimal
    available_amount: Decimal
    state: str
    state_label: str
    existing_editable_note: Optional[Invoice]
    partial_block_reason: str
    lines: tuple[CreditLineSummary, ...]


def credit_summary(invoice: Invoice, *, exclude_note_id=None) -> CreditSummary:
    if invoice.document_type != 11 or invoice.status != 'authorized':
        raise ValidationError('Solo se puede calcular el saldo de una Factura C autorizada.')
    notes = list(invoice.credit_notes.exclude(pk=exclude_note_id).prefetch_related('lines').order_by('created_at'))
    committed = [note for note in notes if note.status in COMMITTED_CREDIT_STATES]
    authorized_amount = sum((note.total for note in committed if note.status == 'authorized'), ZERO)
    reserved_amount = sum((note.total for note in committed if note.status in RESERVED_CREDIT_STATES), ZERO)
    available_amount = max(invoice.total - authorized_amount - reserved_amount, ZERO)
    editable = next((note for note in notes if note.status in EDITABLE_STATES), None)

    authorized_quantities = {}
    reserved_quantities = {}
    partial_block_reason = ''
    for note in committed:
        for line in note.lines.all():
            if line.original_line_id:
                target = authorized_quantities if note.status == 'authorized' else reserved_quantities
                target[line.original_line_id] = target.get(line.original_line_id, Decimal('0')) + line.quantity
            elif note.cancellation_kind != 'total' and available_amount > ZERO:
                partial_block_reason = (
                    'Hay una nota de crédito histórica sin correspondencia verificable entre renglones. '
                    'Revisala antes de preparar una anulación parcial.'
                )

    line_summaries = []
    for line in invoice.lines.all():
        authorized = authorized_quantities.get(line.pk, Decimal('0'))
        reserved = reserved_quantities.get(line.pk, Decimal('0'))
        line_summaries.append(CreditLineSummary(
            line=line,
            original_quantity=line.quantity,
            authorized_quantity=authorized,
            reserved_quantity=reserved,
            available_quantity=max(line.quantity - authorized - reserved, Decimal('0')),
        ))

    if editable:
        state, label = 'draft', 'Anulación en preparación'
    elif reserved_amount > ZERO:
        state, label = 'pending', 'Anulación pendiente'
    elif available_amount == ZERO:
        state, label = 'cancelled', 'Anulada totalmente'
    elif authorized_amount > ZERO:
        state, label = 'partial', 'Anulada parcialmente'
    else:
        state, label = 'open', 'Sin anulaciones'
    return CreditSummary(
        invoice=invoice,
        original_total=invoice.total,
        authorized_amount=authorized_amount,
        reserved_amount=reserved_amount,
        available_amount=available_amount,
        state=state,
        state_label=label,
        existing_editable_note=editable,
        partial_block_reason=partial_block_reason,
        lines=tuple(line_summaries),
    )


def _require_admin(user):
    if not user or not user.is_authenticated or not user.is_active or not user.is_superuser:
        raise PermissionError('Solo los administradores de devLink pueden operar facturación.')


def _validated_reason(reason):
    reason = str(reason or '').strip()
    if not reason:
        raise ValidationError('Ingresá el motivo de la anulación.')
    if len(reason) > 500:
        raise ValidationError('El motivo de la anulación no puede superar los 500 caracteres.')
    return reason


def _base_credit_note(original, kind, reason, user):
    today = timezone.localdate()
    return Invoice.objects.create(
        configuration=original.configuration,
        customer=original.customer,
        original=original,
        document_type=13,
        cancellation_kind=kind,
        cancellation_reason=reason,
        issue_date=today,
        concept=original.concept,
        service_from=original.service_from,
        service_to=original.service_to,
        due_date=today if original.concept in (2, 3) else None,
        created_by=user,
    )


def _ensure_available(summary):
    if summary.existing_editable_note:
        raise ValidationError(
            f'La factura {summary.invoice.fiscal_number} ya tiene una nota de crédito editable. '
            'Continuá ese borrador o descartalo antes de crear otro.'
        )
    if summary.reserved_amount > ZERO:
        raise ValidationError(
            f'La factura {summary.invoice.fiscal_number} tiene una anulación pendiente de respuesta. '
            'Conciliá ese comprobante antes de continuar.'
        )
    if summary.available_amount <= ZERO:
        raise ValidationError(f'La factura {summary.invoice.fiscal_number} ya está anulada totalmente.')


def prepare_total_credits(customer_id, invoice_ids, reason, user):
    """Create one exact-balance credit-note draft for every selected invoice."""
    _require_admin(user)
    reason = _validated_reason(reason)
    unique_ids = list(dict.fromkeys(invoice_ids or []))
    if not unique_ids:
        raise ValidationError('Seleccioná al menos una factura para anular.')

    with transaction.atomic():
        invoices = list(
            Invoice.objects.select_for_update()
            .filter(pk__in=unique_ids, customer_id=customer_id, document_type=11, status='authorized')
            .select_related('configuration', 'customer')
            .prefetch_related('lines')
            .order_by('pk')
        )
        if len(invoices) != len(unique_ids):
            raise ValidationError('Una o más facturas seleccionadas no pertenecen al cliente o no están autorizadas.')

        prepared = []
        for original in invoices:
            summary = credit_summary(original)
            _ensure_available(summary)
            note = _base_credit_note(original, 'total', reason, user)
            InvoiceLine.objects.create(
                invoice=note,
                description=f'Anulación total de Factura C {original.fiscal_number}',
                quantity=Decimal('1'),
                unit_price=summary.available_amount,
            )
            Invoice.objects.filter(pk=note.pk).update(total=summary.available_amount)
            note.refresh_from_db()
            prepared.append(note)
        return prepared


def prepare_partial_credit(invoice_id, quantities, reason, user, *, imported_lines_confirmed=False):
    """Create a partial credit-note draft linked to the selected original lines."""
    _require_admin(user)
    reason = _validated_reason(reason)
    quantities = quantities or {}

    with transaction.atomic():
        try:
            original = (
                Invoice.objects.select_for_update()
                .select_related('configuration', 'customer')
                .prefetch_related('lines')
                .get(pk=invoice_id, document_type=11, status='authorized')
            )
        except Invoice.DoesNotExist as exc:
            raise ValidationError('La factura seleccionada no está autorizada o no existe.') from exc

        summary = credit_summary(original)
        _ensure_available(summary)
        if summary.partial_block_reason:
            raise ValidationError(summary.partial_block_reason)
        if original.source == 'import' and not imported_lines_confirmed:
            raise ValidationError(
                'Confirmá que los renglones cargados coinciden con el PDF original antes de preparar una anulación parcial.'
            )

        requested = {}
        for raw_line_id, raw_quantity in quantities.items():
            try:
                quantity = Decimal(str(raw_quantity or '0'))
            except (InvalidOperation, ValueError):
                raise ValidationError('Ingresá cantidades válidas para la anulación parcial.')
            if quantity < 0:
                raise ValidationError('Las cantidades a anular no pueden ser negativas.')
            if quantity > 0:
                requested[str(raw_line_id)] = quantity
        if not requested:
            raise ValidationError('Seleccioná al menos un renglón y una cantidad para anular.')

        selected = []
        for line_summary in summary.lines:
            quantity = requested.pop(str(line_summary.line.pk), None)
            if quantity is None:
                continue
            if quantity > line_summary.available_quantity:
                raise ValidationError(
                    f'La cantidad indicada para “{line_summary.line.description}” supera el saldo disponible '
                    f'({line_summary.available_quantity}).'
                )
            selected.append((line_summary.line, quantity))
        if requested:
            raise ValidationError('Uno de los renglones seleccionados no pertenece a la factura.')

        total = sum(
            ((quantity * line.unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
             for line, quantity in selected),
            ZERO,
        )
        if total <= ZERO:
            raise ValidationError('La anulación parcial debe tener un importe mayor a cero.')
        if total > summary.available_amount:
            raise ValidationError(f'La nota excede el saldo acreditable: $ {summary.available_amount:.2f}.')

        note = _base_credit_note(original, 'partial', reason, user)
        for line, quantity in selected:
            InvoiceLine.objects.create(
                invoice=note,
                original_line=line,
                description=line.description,
                quantity=quantity,
                unit_price=line.unit_price,
            )
        Invoice.objects.filter(pk=note.pk).update(total=total)
        note.refresh_from_db()
        return note


def discard_credit_draft(invoice_id, user):
    _require_admin(user)
    with transaction.atomic():
        try:
            note = Invoice.objects.select_for_update().get(pk=invoice_id, document_type=13)
        except Invoice.DoesNotExist as exc:
            raise ValidationError('La nota de crédito no existe.') from exc
        if note.status not in EDITABLE_STATES:
            raise ValidationError('Solo se pueden descartar notas de crédito en borrador o rechazadas.')
        note.delete()
