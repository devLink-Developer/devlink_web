"""Persist-before-send coordination; DB locks protect every claim and credit balance."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .arca import ArcaClient, valid_cae
from .credits import credit_summary
from .models import ArcaConfiguration, Invoice, InvoiceAttempt, EDITABLE_STATES, PENDING_STATES
from .validation import invoice_payload, snapshots, validate_invoice
from .locks import configuration_operation


def require_admin(user):
    if not user or not user.is_authenticated or not user.is_active or not user.is_superuser:
        raise PermissionError('Solo los administradores de devLink pueden operar facturación.')


def _lock(invoice_id, expected_configuration=None):
    configuration_id = Invoice.objects.values_list('configuration_id', flat=True).get(pk=invoice_id)
    config = ArcaConfiguration.objects.select_for_update().select_related('issuer').get(pk=configuration_id)
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.configuration_id != config.pk or (expected_configuration is not None and config.pk != expected_configuration):
        raise ValidationError('El borrador cambió de configuración. Revisá los datos actuales y volvé a intentar.')
    invoice.configuration = config
    return config, invoice


def _credit_balance(invoice):
    if invoice.document_type != 13:
        return
    original = Invoice.objects.select_for_update().get(pk=invoice.original_id)
    summary = credit_summary(original, exclude_note_id=invoice.pk)
    if invoice.total > summary.available_amount:
        raise ValidationError(f'La nota excede el saldo acreditable: $ {summary.available_amount:.2f}.')
    if invoice.cancellation_kind == 'total' and invoice.total != summary.available_amount:
        raise ValidationError('La anulación total debe cubrir exactamente el saldo disponible de la factura.')
    if invoice.cancellation_kind == 'partial':
        available_by_line = {item.line.pk: item.available_quantity for item in summary.lines}
        requested_by_line = {}
        for line in invoice.lines.select_related('original_line'):
            if not line.original_line_id or line.original_line.invoice_id != original.pk:
                raise ValidationError('La anulación parcial contiene un renglón sin correspondencia con la factura original.')
            if line.unit_price != line.original_line.unit_price:
                raise ValidationError('La anulación parcial debe conservar el precio unitario original.')
            requested_by_line[line.original_line_id] = (
                requested_by_line.get(line.original_line_id, Decimal('0')) + line.quantity
            )
        for line_id, requested in requested_by_line.items():
            if requested > available_by_line.get(line_id, Decimal('0')):
                raise ValidationError('La cantidad a anular supera el saldo disponible del renglón original.')


def _complete_approval(result, invoice):
    return (isinstance(result, dict) and result.get('outcome') == 'authorized'
        and result.get('number') == invoice.number and result.get('document_type') == invoice.document_type
        and result.get('point_of_sale') == invoice.point_of_sale
        and valid_cae(str(result.get('cae', '')), str(result.get('cae_due', ''))))


def _safe_result(result):
    if not isinstance(result, dict):
        return {'outcome': 'unknown', 'messages': []}
    allowed = ('outcome', 'number', 'document_type', 'point_of_sale', 'cae', 'cae_due', 'document_number',
               'document_id_type', 'concept', 'issue_date', 'total', 'messages', 'currency', 'exchange_rate',
               'service_from', 'service_to', 'due_date', 'fiscal')
    return {key: result[key] for key in allowed if key in result}


def _persist_outcome(invoice, attempt, result, *, not_found=False):
    result = _safe_result(result)
    changes = {'updated_at': timezone.now()}
    if _complete_approval(result, invoice):
        changes.update(status='authorized', cae=result['cae'],
            cae_due=datetime.strptime(result['cae_due'], '%Y%m%d').date(), last_message='Autorizado por ARCA.')
    elif result.get('outcome') == 'rejected' or not_found:
        changes.update(status='rejected', number=None, cae='', cae_due=None,
            last_message='ARCA rechazó el comprobante.' if not not_found else 'ARCA confirmó que no existe. Podés revisar y reintentar manualmente.')
    else:
        changes.update(status='unknown', last_message='ARCA no confirmó el resultado. Conciliá antes de volver a emitir.')
    if changes['status'] != 'authorized' and result.get('messages'):
        changes['last_message'] += ' ' + ' · '.join(
            f'{str(m.get("code", ""))[:20]}: {str(m.get("message", ""))[:500]}'
            for m in result['messages'][:10] if isinstance(m, dict))
    Invoice.objects.filter(pk=invoice.pk).update(**changes)
    InvoiceAttempt.objects.filter(pk=attempt.pk).update(outcome=changes['status'], response=result, finished_at=timezone.now())
    invoice.refresh_from_db()
    return invoice


def issue_invoice(invoice_id, user):
    require_admin(user)
    configuration_id = Invoice.objects.values_list('configuration_id', flat=True).get(pk=invoice_id)
    with configuration_operation(configuration_id):
        invoice = Invoice.objects.select_related('configuration__issuer').get(pk=invoice_id)
        if invoice.configuration_id != configuration_id:
            raise ValidationError('El borrador cambió de configuración. Volvé a revisarlo.')
        if invoice.status == 'authorized' or invoice.status in PENDING_STATES:
            return invoice
        config = invoice.configuration
        if not config.enabled or (config.environment == 'PROD' and not settings.BILLING_ALLOW_PRODUCTION):
            raise ValidationError('La emisión está deshabilitada para este ambiente.')
        config.full_clean()
        validate_invoice(invoice)
        client = ArcaClient(config)
        # TA issuance must commit independently before any rollback-prone numbering transaction.
        client.prepare()
        return _issue_invoice(invoice_id, user, configuration_id, client)


def _issue_invoice(invoice_id, user, configuration_id, client):
    require_admin(user)
    with transaction.atomic():
        config, invoice = _lock(invoice_id, configuration_id)
        if invoice.status == 'authorized' or invoice.status in PENDING_STATES:
            return invoice
        if invoice.status not in EDITABLE_STATES:
            raise ValidationError('Este comprobante no admite emisión.')
        config.full_clean()
        if not config.enabled:
            raise ValidationError('La emisión está deshabilitada en esta configuración.')
        if config.environment == 'PROD' and not settings.BILLING_ALLOW_PRODUCTION:
            raise ValidationError('El servidor no tiene habilitada la emisión de producción.')
        issuer = config.issuer
        if not issuer.address.strip() or not issuer.gross_income.strip() or not issuer.activities_since:
            raise ValidationError('Completá los datos fiscales del emisor antes de emitir.')
        validate_invoice(invoice)
        _credit_balance(invoice)
        if Invoice.objects.filter(environment=config.environment, point_of_sale=config.point_of_sale,
                document_type=invoice.document_type, status__in=PENDING_STATES).exclude(pk=invoice.pk).exists():
            raise ValidationError('Hay un comprobante de esta serie pendiente de conciliación.')
        uncertain_attempt = invoice.attempts.filter(operation='authorize', outcome__in=PENDING_STATES).first()
        if uncertain_attempt and (uncertain_attempt.fiscal_context.get('environment') != config.environment
                or uncertain_attempt.fiscal_context.get('point_of_sale') != config.point_of_sale):
            raise ValidationError('Hay un intento previo incierto en otra serie. Verificá ese comprobante en ARCA antes de cambiar de punto de venta o ambiente.')
        remote_last = client.last_number(invoice.document_type)
        if uncertain_attempt and remote_last >= uncertain_attempt.number:
            raise ValidationError('ARCA ya alcanzó el número de un intento previo que quedó incierto. No se reenviará este borrador con otro número; verificá el comprobante anterior en ARCA.')
        local_last = Invoice.objects.filter(environment=config.environment, point_of_sale=config.point_of_sale,
            document_type=invoice.document_type, status='authorized').aggregate(last=Max('number'))['last'] or 0
        if remote_last < local_last:
            raise ValidationError('ARCA informa un último número menor que el historial registrado. Revisá el punto de venta y su habilitación para webservices; no se emitió otro comprobante.')
        number = remote_last + 1
        if not 1 <= number <= 99999999:
            raise ValidationError('La serie alcanzó el límite de numeración admitido por ARCA.')
        if Invoice.objects.filter(environment=config.environment, point_of_sale=config.point_of_sale,
                document_type=invoice.document_type, number=number).exists():
            raise ValidationError('La secuencia local y ARCA no coinciden. Revisá el historial antes de continuar.')
        invoice.number, invoice.point_of_sale, invoice.environment = number, config.point_of_sale, config.environment
        invoice.issuer_snapshot, invoice.customer_snapshot = snapshots(invoice)
        payload = invoice_payload(invoice)
        Invoice.objects.filter(pk=invoice.pk).update(status='sending', number=number, point_of_sale=config.point_of_sale,
            environment=config.environment, issuer_snapshot=invoice.issuer_snapshot, customer_snapshot=invoice.customer_snapshot,
            total=invoice.total, last_message='Enviado a ARCA; pendiente de respuesta.', updated_at=timezone.now())
        attempt = InvoiceAttempt.objects.create(invoice=invoice, number=number, request_payload=payload, user=user,
            fiscal_context={'issuer': invoice.issuer_snapshot, 'customer': invoice.customer_snapshot,
                'environment': invoice.environment, 'point_of_sale': invoice.point_of_sale})
    # Reservation is committed. Any competing process can now see it, even if this process terminates.
    try:
        result = client.authorize(payload)
    except Exception:
        # Never persist exception text: SOAP credentials and transport internals must remain private.
        result = {'outcome': 'unknown', 'messages': []}
    with transaction.atomic():
        _, current = _lock(invoice.pk)
        if current.status != 'sending' or current.attempts.filter(operation='authorize').first().pk != attempt.pk:
            return current
        return _persist_outcome(current, attempt, result)


def _matches_consultation(result, invoice, expected):
    try:
        basic_match = (_complete_approval(result, invoice)
            and str(int(result['document_number'])) == str(int(invoice.customer_snapshot['document_number']))
            and result['document_id_type'] == invoice.customer_snapshot['document_type']
            and result['concept'] == invoice.concept
            and result['issue_date'] == invoice.issue_date.strftime('%Y%m%d')
            and Decimal(str(result['total'])) == invoice.total
            and result['currency'] == 'PES' and Decimal(str(result['exchange_rate'])) == Decimal('1')
            and (invoice.concept == 1 or (
                result.get('service_from') == invoice.service_from.strftime('%Y%m%d')
                and result.get('service_to') == invoice.service_to.strftime('%Y%m%d')
                and result.get('due_date') == invoice.due_date.strftime('%Y%m%d'))))
        if not basic_match:
            return False
        fiscal = result['fiscal']
        detail = expected['FeDetReq']['FECAEDetRequest'][0]
        for field in ('ImpTotal', 'ImpNeto', 'ImpIVA', 'ImpOpEx', 'ImpTotConc', 'ImpTrib'):
            if Decimal(str(fiscal[field])) != Decimal(str(detail[field])):
                return False
        if int(fiscal['CbteHasta']) != int(detail['CbteHasta']) or int(fiscal['CondicionIVAReceptorId']) != int(detail['CondicionIVAReceptorId']):
            return False
        if fiscal['Iva'] or fiscal['Tributos']:
            return False
        expected_associations = detail.get('CbtesAsoc', {}).get('CbteAsoc', [])
        actual_associations = fiscal['CbtesAsoc']
        normalize = lambda entries: sorted(tuple(str(entry.get(key, '')) for key in ('Tipo', 'PtoVta', 'Nro', 'Cuit', 'CbteFch')) for entry in entries)
        return normalize(actual_associations) == normalize(expected_associations)
    except (KeyError, ValueError, TypeError, InvalidOperation):
        return False


def reconcile_invoice(invoice_id, user):
    require_admin(user)
    configuration_id = Invoice.objects.values_list('configuration_id', flat=True).get(pk=invoice_id)
    with configuration_operation(configuration_id):
        invoice = Invoice.objects.select_related('configuration__issuer').get(pk=invoice_id)
        if invoice.status not in PENDING_STATES:
            return invoice
        client = ArcaClient(invoice.configuration)
        client.prepare()
        return _reconcile_invoice(invoice_id, user, configuration_id, client)


def _reconcile_invoice(invoice_id, user, configuration_id, client):
    require_admin(user)
    with transaction.atomic():
        config, invoice = _lock(invoice_id, configuration_id)
        if invoice.status not in PENDING_STATES:
            return invoice
        if invoice.status == 'sending' and timezone.now() < invoice.updated_at + timedelta(seconds=config.timeout * 2 + 30):
            raise ValidationError('La solicitud aún puede estar en curso. Esperá antes de conciliarla.')
        number = invoice.number
        authorization = invoice.attempts.filter(operation='authorize').first()
        authorization_id = authorization.pk if authorization else None
    try:
        result = client.consult(invoice.document_type, number)
    except Exception:
        result = {'outcome': 'unknown', 'messages': []}
    with transaction.atomic():
        _, current = _lock(invoice_id)
        latest = current.attempts.filter(operation='authorize').first()
        if current.status not in PENDING_STATES or current.number != number or (latest.pk if latest else None) != authorization_id:
            return current
        attempt = InvoiceAttempt.objects.create(invoice=current, number=number, operation='consult', user=user)
        if result and result.get('outcome') == 'authorized' and not _matches_consultation(result, current, latest.request_payload if latest else {}):
            result = {'outcome': 'unknown', 'messages': [{'code': 'IDENTIDAD',
                'message': 'La respuesta no coincide con la identidad fiscal, receptor, concepto, fecha o importe de este comprobante.'}]}
        return _persist_outcome(current, attempt, result, not_found=isinstance(result, dict) and result.get('outcome') == 'not_found')
