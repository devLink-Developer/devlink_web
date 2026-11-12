"""Explicit operator import of an existing C invoice; never calls an ARCA endpoint."""
import hashlib
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader

from .arca import valid_cae
from .locks import configuration_operation
from .models import ArcaConfiguration, Customer, Invoice, InvoiceAttempt, InvoiceLine, Issuer
from .services import require_admin
from .validation import validate_invoice


def archive_path(name, *, create=False):
    root = Path(settings.BILLING_ARCHIVE_ROOT).resolve()
    if any(root.is_relative_to(Path(public).resolve()) for public in (settings.BASE_DIR, settings.MEDIA_ROOT, settings.STATIC_ROOT)):
        raise ValidationError('El archivo de comprobantes debe estar fuera de Git y de directorios públicos.')
    if not re.fullmatch(r'[0-9a-f]{64}\.pdf', name):
        raise ValidationError('Nombre de archivo histórico no válido.')
    if create:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = (root / name).resolve()
    if not target.is_relative_to(root):
        raise ValidationError('Ruta de archivo histórico no válida.')
    return target


def original_pdf(invoice):
    path = archive_path(invoice.source_document)
    if not path.is_file() or path.stat().st_size > 10*1024*1024:
        raise ValidationError('No está disponible el PDF original en el archivo privado.')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != invoice.source_sha256:
        raise ValidationError('El PDF archivado no coincide con su huella original.')
    return raw


def _date(value):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise ValidationError('Las fechas de importación deben usar YYYY-MM-DD.') from None


def import_historical_invoice(data, pdf_bytes, user, *, update_issuer=False):
    require_admin(user)
    try:
        return _import(data, pdf_bytes, user, update_issuer=update_issuer)
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValidationError('El manifiesto de importación contiene datos faltantes o inválidos.') from exc


def _import(data, pdf_bytes, user, *, update_issuer):
    if data['environment'] != 'PROD' or int(data['document_type']) != 11:
        raise ValidationError('Este importador registra facturas C existentes de producción.')
    point, number = int(data['point_of_sale']), int(data['number'])
    if not 1 <= point <= 99999 or not 1 <= number <= 99999999:
        raise ValidationError('El punto de venta o número fiscal no es válido.')
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    if digest != data['source_sha256'] or len(pdf_bytes) > 10*1024*1024 or not pdf_bytes.startswith(b'%PDF-'):
        raise ValidationError('El PDF no coincide con la huella declarada o supera el tamaño permitido.')
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=True)
        # ARCA PDFs can have an owner password but permit reading with an empty
        # user password. Reading does not alter or remove the source protection.
        if reader.is_encrypted and not reader.decrypt(''):
            raise ValueError('A read password is required')
        if not 1 <= len(reader.pages) <= 20:
            raise ValueError('Unsupported PDF')
        source_text = re.sub(r'\s+', ' ', ' '.join(p.extract_text() for p in reader.pages))
        source_layout = '\n'.join(p.extract_text(extraction_mode='layout') for p in reader.pages)
    except Exception as exc:
        raise ValidationError('No se pudo leer el PDF original para comprobar su identificación.') from exc
    issue_date = _date(data['issue_date'])
    cae_due = _date(data['cae_due'])
    cae = str(data['cae'])
    total = Decimal(str(data['total']))
    if not total.is_finite() or not valid_cae(cae, cae_due.strftime('%Y%m%d')) or cae_due < issue_date:
        raise ValidationError('El CAE, su vencimiento o el importe no son válidos.')
    required_text = [str(data['issuer']['cuit']), str(data['customer']['document_number']),
        f'{point:05d}', f'{number:08d}', cae, issue_date.strftime('%d/%m/%Y')]
    identified = all(re.search(r'(?<!\d)' + re.escape(value) + r'(?!\d)', source_text) for value in required_text)
    # Read the labeled invoice total, not any amount (or a suffix of one) that
    # happens to occur in a line item. Layout extraction restores label/value rows.
    total_pattern = re.compile(r'\b(?:Importe[ \t]+Total|Total)[ \t]*:?[ \t]*(?:ARS[ \t]*)?\$?[ \t]*(\d[\d. ]*,\d{2})(?!\d)', re.IGNORECASE)
    labeled_totals = {Decimal(value.replace(' ', '').replace('.', '').replace(',', '.'))
        for value in total_pattern.findall(source_layout)}
    if not identified or labeled_totals != {total}:
        raise ValidationError('La identificación, fecha, CAE o total del manifiesto no coincide con el PDF.')
    with configuration_operation(0), transaction.atomic():
        identity = {'environment': 'PROD', 'point_of_sale': point, 'document_type': 11, 'number': number}
        existing = Invoice.objects.filter(**identity).first()
        if existing:
            if (existing.source_sha256 == digest and existing.cae == cae and existing.total == total
                    and existing.issue_date == issue_date):
                return existing
            raise ValidationError('Ya existe un comprobante diferente con esa identidad fiscal; no se sobrescribió.')
        if Invoice.objects.filter(source_sha256=digest).exists():
            raise ValidationError('Este PDF ya fue registrado con otra identidad fiscal.')
        issuer_data = data['issuer']
        issuer = Issuer.objects.first()
        if issuer and issuer.cuit != str(issuer_data['cuit']):
            raise ValidationError('El CUIT del PDF no coincide con el emisor de devLink.')
        issuer = issuer or Issuer()
        for field in ('name', 'cuit', 'address', 'gross_income', 'activities_since'):
            value = _date(issuer_data[field]) if field == 'activities_since' else str(issuer_data[field])
            if update_issuer or issuer._state.adding or getattr(issuer, field) in ('', None):
                setattr(issuer, field, value)
        issuer.full_clean()
        issuer.save()
        config, _ = ArcaConfiguration.objects.get_or_create(environment='PROD', defaults={'issuer': issuer, 'point_of_sale': point})
        if not config.point_of_sale:
            config.point_of_sale = point
            config.full_clean()
            config.save(update_fields=['point_of_sale'])
        customer_data = data['customer']
        customer = Customer.objects.filter(document_type=int(customer_data['document_type']),
            document_number=str(customer_data['document_number'])).first()
        if customer is None:
            customer = Customer(**{field: customer_data[field] for field in
                ('name', 'document_type', 'document_number', 'vat_condition', 'address')})
            customer.full_clean()
            customer.save()
        invoice = Invoice.objects.create(configuration=config, customer=customer, issue_date=issue_date,
            concept=int(data['concept']), service_from=_date(data['service_from']) if data.get('service_from') else None,
            service_to=_date(data['service_to']) if data.get('service_to') else None,
            due_date=_date(data['due_date']) if data.get('due_date') else None, created_by=user,
            environment='PROD', point_of_sale=point, number=number, source='import',
            notes='Comprobante existente registrado desde su PDF original. No se solicitó una nueva autorización.')
        for values in data['lines']:
            line = InvoiceLine(invoice=invoice, description=str(values['description']),
                quantity=Decimal(str(values['quantity'])), unit_price=Decimal(str(values['unit_price'])))
            line.full_clean()
            line.save()
        validate_invoice(invoice, historical=True)
        if invoice.total != total:
            raise ValidationError('La suma de las líneas no coincide con el total declarado.')
        filename = digest + '.pdf'
        target = archive_path(filename, create=True)
        try:
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValidationError('Existe otro archivo en el destino privado; no se sobrescribió.')
        else:
            with os.fdopen(descriptor, 'wb') as file:
                file.write(pdf_bytes)
        Invoice.objects.filter(pk=invoice.pk).update(status='authorized', total=total,
            issuer_snapshot=issuer_data, customer_snapshot=customer_data, cae=cae, cae_due=cae_due,
            source_document=filename, source_sha256=digest,
            last_message='Comprobante existente incorporado desde PDF. Sin reenvío a ARCA.', updated_at=timezone.now())
        invoice.refresh_from_db()
        InvoiceAttempt.objects.create(invoice=invoice, number=number, operation='import', outcome='authorized', user=user,
            request_payload={'source_sha256': digest}, fiscal_context={'issuer': issuer_data, 'customer': customer_data,
                'environment': 'PROD', 'point_of_sale': point}, response={'source': 'PDF original'}, finished_at=timezone.now())
        return invoice
