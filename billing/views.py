from decimal import Decimal
from functools import wraps

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Max, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .arca import ArcaClient, certificate_material
from .credits import credit_summary, discard_credit_draft, prepare_partial_credit, prepare_total_credits
from .forms import (CancellationSelectionForm, ConfigurationForm, CustomerForm, InvoiceForm,
    IssuerForm, LineFormSet, PartialCancellationForm)
from .models import ArcaConfiguration, Customer, Invoice, Issuer
from .services import issue_invoice, reconcile_invoice
from .validation import validate_invoice
from .locks import configuration_operation


def admin_only(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_superuser:
            return HttpResponseForbidden('Acceso exclusivo de administración de devLink.')
        response = view(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response
    return wrapped


@admin_only
def dashboard(request):
    invoices = Invoice.objects.select_related('customer')
    status = request.GET.get('status', '')
    environment = request.GET.get('environment', '')
    query = request.GET.get('q', '').strip()[:100]
    if status in dict(Invoice.STATUS_CHOICES):
        invoices = invoices.filter(status=status)
    if environment in ('HOMO', 'PROD'):
        invoices = invoices.filter(environment=environment) | invoices.filter(environment='', configuration__environment=environment)
    if query:
        invoices = invoices.filter(Q(customer__name__icontains=query) | Q(customer_snapshot__name__icontains=query) | Q(cae__icontains=query))
    authorized = Invoice.objects.filter(status='authorized', environment='PROD')
    billed = authorized.filter(document_type=11).aggregate(total=Sum('total'))['total'] or Decimal('0')
    credited = authorized.filter(document_type=13).aggregate(total=Sum('total'))['total'] or Decimal('0')
    production = ArcaConfiguration.objects.filter(environment='PROD').first()
    sequence_hint = ''
    if production and production.point_of_sale:
        last = authorized.filter(document_type=11, point_of_sale=production.point_of_sale).aggregate(last=Max('number'))['last']
        if last is not None:
            sequence_hint = f'{production.point_of_sale:05d}-{last+1:08d}'
    return render(request, 'billing/dashboard.html', {'page': Paginator(invoices, 25).get_page(request.GET.get('page')),
        'statuses': Invoice.STATUS_CHOICES, 'selected_status': status, 'selected_environment': environment, 'query': query,
        'net_total': billed - credited, 'draft_count': Invoice.objects.filter(status__in=['draft', 'rejected']).count(),
        'pending_count': Invoice.objects.filter(status__in=['sending', 'unknown']).count(),
        'configured': ArcaConfiguration.objects.exists(), 'sequence_hint': sequence_hint})


@admin_only
@require_http_methods(['GET', 'POST'])
def fiscal_settings(request):
    env = request.GET.get('environment', 'PROD')
    env = env if env in ('PROD', 'HOMO') else 'PROD'
    issuer = Issuer.objects.first() or Issuer()
    config = ArcaConfiguration.objects.filter(environment=env).first() or ArcaConfiguration(environment=env, issuer=issuer)
    issuer_form = IssuerForm(request.POST or None, instance=issuer, prefix='issuer')
    config_form = ConfigurationForm(request.POST or None, instance=config, prefix='arca')
    if request.method == 'POST':
        issuer_valid, config_valid = issuer_form.is_valid(), config_form.is_valid()
        if issuer_valid and config_valid:
            try:
                with configuration_operation(config.pk or 0):
                    with transaction.atomic():
                        if config.pk:
                            ArcaConfiguration.objects.select_for_update().get(pk=config.pk)
                        issuer = issuer_form.save()
                        config = config_form.save(commit=False)
                        config.issuer = issuer
                        config.full_clean()
                        activate = config.enabled
                        config.enabled = False
                        config.save()
                    # Configuration is safely disabled and committed before WSAA issues a ticket.
                    if activate:
                        if env == 'PROD' and not django_settings.BILLING_ALLOW_PRODUCTION:
                            raise ValidationError('El servidor debe habilitar BILLING_ALLOW_PRODUCTION antes de activar este ambiente.')
                        if not issuer.address or not issuer.gross_income or not issuer.activities_since:
                            raise ValidationError('Completá domicilio, ingresos brutos e inicio de actividades.')
                        certificate_material(config)
                        points = ArcaClient(config).points_of_sale()
                        if not any(p['number'] == config.point_of_sale and not p['blocked'] and not p['closed']
                                and p['emission_type'] == 'CAE' for p in points):
                            raise ValidationError('El punto de venta no figura activo para emisión CAE por webservices.')
                        with transaction.atomic():
                            ArcaConfiguration.objects.select_for_update().get(pk=config.pk)
                            config.enabled = True
                            config.save(update_fields=['enabled'])
                messages.success(request, 'Configuración fiscal guardada.')
                return redirect(request.path + '?environment=' + env)
            except ValidationError as exc:
                config_form.add_error(None, ' '.join(exc.messages))
            except Exception:
                config_form.add_error(None, 'No se pudo verificar ARCA. La configuración no se activó; revisá certificado y conexión.')
    return render(request, 'billing/settings.html', {'issuer_form': issuer_form, 'config_form': config_form,
        'configuration': config, 'environment': env, 'production_allowed': django_settings.BILLING_ALLOW_PRODUCTION,
        'private_root_configured': bool(django_settings.BILLING_CERTIFICATE_ROOT)})


@admin_only
@require_POST
def diagnostics(request, configuration_id):
    config = get_object_or_404(ArcaConfiguration.objects.select_related('issuer'), pk=configuration_id)
    result, problem = None, ''
    try:
        material = certificate_material(config)
        client = ArcaClient(config)
        result = {'serial': material['serial'], 'expires_at': material['expires_at'],
            'status': client.status(), 'points': client.points_of_sale()}
    except ValidationError as exc:
        problem = ' '.join(exc.messages)
    except Exception:
        problem = 'No se pudo consultar ARCA. Revisá conexión, certificado y autorización del servicio wsfe.'
    return render(request, 'billing/diagnostics.html', {'configuration': config, 'result': result, 'problem': problem})


@admin_only
def customers(request):
    query = request.GET.get('q', '').strip()[:100]
    items = Customer.objects.all()
    if query:
        items = items.filter(Q(name__icontains=query) | Q(document_number__icontains=query))
    return render(request, 'billing/customers.html', {'page': Paginator(items, 25).get_page(request.GET.get('page')), 'query': query})


@admin_only
@require_http_methods(['GET', 'POST'])
def cancellations(request):
    selected_customer = None
    if request.method == 'GET':
        try:
            selected_customer = Customer.objects.filter(pk=request.GET.get('customer')).first()
        except (TypeError, ValueError):
            selected_customer = None
    form = CancellationSelectionForm(request.POST or None, customer=selected_customer)
    if request.method == 'POST' and form.is_valid():
        selected_customer = form.cleaned_data['customer']
        try:
            notes = prepare_total_credits(
                selected_customer.pk,
                [invoice.pk for invoice in form.cleaned_data['invoices']],
                form.cleaned_data['reason'],
                request.user,
            )
            if len(notes) == 1:
                messages.success(request, 'La nota de crédito quedó preparada para revisión. Todavía no se envió a ARCA.')
                return redirect('billing:detail', invoice_id=notes[0].pk)
            messages.success(request, f'Se prepararon {len(notes)} notas de crédito. Todavía no se enviaron a ARCA.')
            return redirect(f'{request.path}?customer={selected_customer.pk}')
        except ValidationError as exc:
            form.add_error(None, ' '.join(exc.messages))
    elif request.method == 'POST':
        selected_customer = form.customer

    summaries = []
    if selected_customer:
        invoices = (Invoice.objects.filter(customer=selected_customer, document_type=11, status='authorized')
            .select_related('customer', 'configuration').prefetch_related('lines', 'credit_notes__lines')
            .order_by('-issue_date', '-created_at'))
        summaries = [credit_summary(invoice) for invoice in invoices]
    return render(request, 'billing/cancellations.html', {
        'form': form,
        'customers': Customer.objects.order_by('name'),
        'selected_customer': selected_customer,
        'summaries': summaries,
        'selected_invoice': request.GET.get('invoice', ''),
    })


@admin_only
@require_http_methods(['GET', 'POST'])
def cancellation_partial(request, invoice_id):
    original = get_object_or_404(
        Invoice.objects.select_related('customer', 'configuration').prefetch_related('lines'),
        pk=invoice_id,
        document_type=11,
        status='authorized',
    )
    summary = credit_summary(original)
    if summary.existing_editable_note:
        messages.info(request, 'Esta factura ya tiene una nota de crédito en preparación.')
        return redirect('billing:detail', invoice_id=summary.existing_editable_note.pk)
    form = PartialCancellationForm(request.POST or None, summary=summary)
    if request.method == 'POST' and form.is_valid():
        try:
            note = prepare_partial_credit(
                original.pk,
                form.quantities(),
                form.cleaned_data['reason'],
                request.user,
                imported_lines_confirmed=form.cleaned_data.get('confirm_imported', False),
            )
            messages.success(request, 'La nota de crédito quedó preparada para revisión. Todavía no se envió a ARCA.')
            return redirect('billing:detail', invoice_id=note.pk)
        except ValidationError as exc:
            form.add_error(None, ' '.join(exc.messages))
    return render(request, 'billing/cancellation_partial.html', {
        'form': form,
        'summary': summary,
        'invoice': original,
        'partial_rows': [{'field': form[name], 'summary': item} for name, item in form.line_fields],
    })


@admin_only
@require_http_methods(['GET', 'POST'])
def customer_form(request, customer_id=None):
    customer = get_object_or_404(Customer, pk=customer_id) if customer_id else Customer()
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Cliente fiscal guardado.')
        return redirect('billing:customers')
    return render(request, 'billing/customer_form.html', {'form': form, 'customer': customer})


@admin_only
@require_http_methods(['GET', 'POST'])
def invoice_form(request, invoice_id=None):
    with transaction.atomic():
        invoice = get_object_or_404(Invoice.objects.select_for_update(), pk=invoice_id) if invoice_id else Invoice(created_by=request.user)
        if invoice.original_id:
            return HttpResponse('Las notas de crédito se administran desde el centro de anulaciones.', status=409)
        if not invoice.editable:
            return HttpResponse('Este comprobante es inmutable.', status=409)
        form = InvoiceForm(request.POST or None, instance=invoice)
        formset = LineFormSet(request.POST or None, instance=invoice, prefix='lines')
        if request.method == 'POST':
            valid_form, valid_lines = form.is_valid(), formset.is_valid()
            if valid_form and valid_lines:
                try:
                    # A savepoint also rolls back the draft if aggregate validation fails.
                    with transaction.atomic():
                        invoice = form.save(commit=False)
                        invoice.total = sum((f.instance.amount for f in formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')), Decimal('0'))
                        invoice.save()
                        formset.instance = invoice
                        formset.save()
                        validate_invoice(invoice)
                        invoice.save(update_fields=['total', 'updated_at'])
                    messages.success(request, 'Borrador guardado. Todavía no se envió a ARCA.')
                    return redirect('billing:detail', invoice_id=invoice.pk)
                except ValidationError as exc:
                    form.add_error(None, ' '.join(exc.messages))
    return render(request, 'billing/invoice_form.html', {'form': form, 'formset': formset, 'invoice': invoice})


@admin_only
def detail(request, invoice_id):
    invoice = get_object_or_404(Invoice.objects.select_related('customer', 'configuration', 'original')
        .prefetch_related('lines', 'credit_notes__lines'), pk=invoice_id)
    cancellation_summary = None
    related_credit_notes = []
    if invoice.document_type == 11 and invoice.status == 'authorized':
        cancellation_summary = credit_summary(invoice)
        related_credit_notes = invoice.credit_notes.select_related('created_by').order_by('-created_at')
    receiver = (invoice.original.customer_snapshot if invoice.document_type == 13 and invoice.editable
        else invoice.customer if invoice.editable else invoice.customer_snapshot)
    return render(request, 'billing/detail.html', {'invoice': invoice, 'attempts': invoice.attempts.all()[:30],
        'issuer': invoice.configuration.issuer if invoice.editable else invoice.issuer_snapshot,
        'receiver': receiver,
        'display_point_of_sale': invoice.configuration.point_of_sale if invoice.editable else invoice.point_of_sale,
        'cancellation_summary': cancellation_summary, 'related_credit_notes': related_credit_notes})


@admin_only
@require_POST
def issue(request, invoice_id):
    get_object_or_404(Invoice, pk=invoice_id)
    if request.POST.get('confirm') != 'yes':
        messages.error(request, 'Confirmá la revisión de los datos antes de emitir.')
        return redirect('billing:detail', invoice_id=invoice_id)
    try:
        invoice = issue_invoice(invoice_id, request.user)
        messages.add_message(request, messages.SUCCESS if invoice.status == 'authorized' else messages.WARNING, invoice.last_message)
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    return redirect('billing:detail', invoice_id=invoice_id)


@admin_only
@require_POST
def reconcile(request, invoice_id):
    get_object_or_404(Invoice, pk=invoice_id)
    try:
        invoice = reconcile_invoice(invoice_id, request.user)
        messages.add_message(request, messages.SUCCESS if invoice.status == 'authorized' else messages.WARNING, invoice.last_message)
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    return redirect('billing:detail', invoice_id=invoice_id)


@admin_only
@require_POST
def credit_note(request, invoice_id):
    original = get_object_or_404(Invoice.objects.prefetch_related('lines'), pk=invoice_id,
        document_type=11, status='authorized')
    summary = credit_summary(original)
    if summary.existing_editable_note:
        messages.info(request, 'Esta factura ya tiene una nota de crédito en preparación.')
        return redirect('billing:detail', invoice_id=summary.existing_editable_note.pk)
    return redirect('billing:cancellation_partial', invoice_id=original.pk)


@admin_only
@require_POST
def credit_discard(request, invoice_id):
    note = get_object_or_404(Invoice, pk=invoice_id, document_type=13)
    customer_id = note.customer_id
    try:
        discard_credit_draft(note.pk, request.user)
        messages.success(request, 'El borrador de nota de crédito fue descartado.')
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
    return redirect(f"{reverse('billing:cancellations')}?customer={customer_id}")


@admin_only
def pdf(request, invoice_id):
    from .pdf import invoice_pdf
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    if invoice.status != 'authorized' or not invoice.cae:
        return HttpResponse('Solo los comprobantes autorizados tienen PDF fiscal.', status=409)
    try:
        if invoice.source_document:
            from .importing import original_pdf
            raw = original_pdf(invoice)
        else:
            raw = invoice_pdf(invoice)
    except ValidationError as exc:
        return HttpResponse(' '.join(exc.messages), status=409)
    response = HttpResponse(raw, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="devlink-{invoice.document_type}-{invoice.fiscal_number}.pdf"'
    return response
