import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


ENVIRONMENTS = [('HOMO', 'Homologación'), ('PROD', 'Producción')]
DOCUMENT_TYPES = [(11, 'Factura C'), (13, 'Nota de crédito C')]
CANCELLATION_KINDS = [('total', 'Anulación total'), ('partial', 'Anulación parcial')]
VAT_CONDITIONS = [(1, 'IVA Responsable Inscripto'), (4, 'IVA Sujeto Exento'),
    (5, 'Consumidor Final'), (6, 'Responsable Monotributo'), (7, 'Sujeto No Categorizado'),
    (8, 'Proveedor del Exterior'), (9, 'Cliente del Exterior'), (10, 'IVA Liberado – Ley 19.640'),
    (13, 'Monotributista Social'), (15, 'IVA No Alcanzado'), (16, 'Monotributo Trabajador Independiente Promovido')]
EDITABLE_STATES = ('draft', 'rejected')
PENDING_STATES = ('sending', 'unknown')


class Issuer(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    name = models.CharField('Razón social', max_length=200, default='Eudy David Espinoza Leal')
    cuit = models.CharField('CUIT', max_length=11, default='20959815926')
    address = models.CharField('Domicilio fiscal', max_length=255, blank=True)
    gross_income = models.CharField('Ingresos brutos', max_length=80, blank=True)
    activities_since = models.DateField('Inicio de actividades', null=True, blank=True)

    def __str__(self):
        return self.name

    def clean(self):
        from .validation import validate_cuit
        validate_cuit(self.cuit)
        if self.pk != 1:
            raise ValidationError('Solo se admite el emisor propio de devLink.')

    def save(self, *args, **kwargs):
        if self.pk != 1 or (self._state.adding and type(self).objects.exists()):
            raise ValidationError('Ya existe el emisor de devLink.')
        if not self._state.adding:
            old = type(self).objects.get(pk=self.pk)
            if old.cuit != self.cuit and Invoice.objects.exclude(status__in=EDITABLE_STATES).exists():
                raise ValidationError('No se puede cambiar el CUIT con comprobantes emitidos o pendientes.')
        return super().save(*args, **kwargs)


class ArcaConfiguration(models.Model):
    issuer = models.ForeignKey(Issuer, on_delete=models.PROTECT, verbose_name='Emisor')
    environment = models.CharField('Ambiente', max_length=4, choices=ENVIRONMENTS, unique=True)
    point_of_sale = models.PositiveIntegerField('Punto de venta', null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(99999)])
    enabled = models.BooleanField('Habilitar emisión', default=False)
    certificate_name = models.CharField('Archivo del certificado (ruta relativa privada)', max_length=220, blank=True)
    private_key_name = models.CharField('Archivo de clave privada (.key)', max_length=220, blank=True)
    password_env = models.CharField('Variable de entorno de la contraseña', max_length=100, blank=True)
    timeout = models.PositiveIntegerField('Tiempo de espera (segundos)', default=30,
        validators=[MinValueValidator(5), MaxValueValidator(120)])
    generation_offset = models.SmallIntegerField('Anticipación del TRA (minutos)', default=-5,
        validators=[MinValueValidator(-10), MaxValueValidator(-1)])
    expiration_window = models.PositiveSmallIntegerField('Ventana del TRA (minutos)', default=10,
        validators=[MinValueValidator(1), MaxValueValidator(60)])

    @property
    def authentication_url(self):
        return {'HOMO': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
                'PROD': 'https://wsaa.afip.gov.ar/ws/services/LoginCms'}[self.environment]

    @property
    def webservice_url(self):
        return {'HOMO': 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx',
                'PROD': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx'}[self.environment]

    def __str__(self):
        return f'{self.get_environment_display()} · PV {self.point_of_sale or "sin configurar"}'

    def clean(self):
        import re
        if self.enabled and not self.point_of_sale:
            raise ValidationError({'point_of_sale': 'Seleccioná un punto de venta antes de habilitar la emisión.'})
        if self.password_env and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', self.password_env):
            raise ValidationError({'password_env': 'Ingresá un nombre de variable, no una contraseña.'})
        if self.pk and Invoice.objects.filter(configuration=self, status__in=PENDING_STATES).exists():
            old = type(self).objects.get(pk=self.pk)
            if any(getattr(old, f) != getattr(self, f) for f in ('environment', 'point_of_sale', 'issuer_id')):
                raise ValidationError('Conciliá los comprobantes pendientes antes de cambiar la identidad fiscal.')


class Customer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name='Cuenta del portal (opcional)')
    name = models.CharField('Nombre o razón social', max_length=200)
    document_type = models.PositiveSmallIntegerField('Tipo de identificación',
        choices=[(80, 'CUIT'), (86, 'CUIL'), (96, 'DNI'), (99, 'Sin identificar')], default=80)
    document_number = models.CharField('Número (sin separadores)', max_length=20)
    vat_condition = models.PositiveSmallIntegerField('Condición frente al IVA', choices=VAT_CONDITIONS, default=5)
    address = models.CharField('Domicilio', max_length=255)
    email = models.EmailField('Correo', blank=True)
    active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} · {self.document_number}'

    def clean(self):
        from .validation import validate_document
        validate_document(self.document_type, self.document_number)


class Invoice(models.Model):
    STATUS_CHOICES = [('draft', 'Borrador'), ('sending', 'En envío'), ('authorized', 'Autorizado'),
        ('rejected', 'Rechazado / corregible'), ('unknown', 'Resultado incierto')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    configuration = models.ForeignKey(ArcaConfiguration, on_delete=models.PROTECT, verbose_name='Configuración ARCA')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name='Cliente')
    document_type = models.PositiveSmallIntegerField('Comprobante', choices=DOCUMENT_TYPES, default=11)
    original = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='credit_notes')
    cancellation_kind = models.CharField('Alcance de la anulación', max_length=7,
        choices=CANCELLATION_KINDS, blank=True)
    cancellation_reason = models.CharField('Motivo de la anulación', max_length=500, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='draft')
    issue_date = models.DateField('Fecha de emisión', default=timezone.localdate)
    concept = models.PositiveSmallIntegerField('Concepto', choices=[(1, 'Productos'), (2, 'Servicios'),
        (3, 'Productos y servicios')], default=2)
    service_from = models.DateField('Servicio desde', null=True, blank=True)
    service_to = models.DateField('Servicio hasta', null=True, blank=True)
    due_date = models.DateField('Vencimiento de pago', null=True, blank=True)
    notes = models.TextField('Notas internas', blank=True)
    environment = models.CharField(max_length=4, choices=ENVIRONMENTS, blank=True)
    point_of_sale = models.PositiveIntegerField(null=True, blank=True)
    number = models.PositiveBigIntegerField(null=True, blank=True)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    issuer_snapshot = models.JSONField(default=dict, blank=True)
    customer_snapshot = models.JSONField(default=dict, blank=True)
    cae = models.CharField(max_length=14, blank=True)
    cae_due = models.DateField(null=True, blank=True)
    last_message = models.TextField(blank=True)
    source = models.CharField(max_length=12, default='wsfe', choices=[('wsfe', 'WSFE'), ('import', 'Comprobante existente')])
    source_document = models.CharField(max_length=80, blank=True)
    source_sha256 = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name='billing_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['environment', 'point_of_sale', 'document_type', 'number'],
            condition=Q(number__isnull=False), name='billing_fiscal_identity_unique')]

    @property
    def editable(self):
        return self.status in EDITABLE_STATES

    @property
    def fiscal_number(self):
        return f'{self.point_of_sale:05d}-{self.number:08d}' if self.point_of_sale and self.number else 'Sin autorizar'

    def __str__(self):
        return f'{self.get_document_type_display()} {self.fiscal_number}'

    def save(self, *args, **kwargs):
        if not self._state.adding and not type(self).objects.get(pk=self.pk).editable:
            raise ValidationError('Este comprobante es inmutable. Usá conciliación o una nota de crédito.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self.editable:
            raise ValidationError('No se pueden borrar comprobantes emitidos o pendientes.')
        return super().delete(*args, **kwargs)


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='lines', on_delete=models.CASCADE)
    original_line = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT,
        related_name='credit_lines', verbose_name='Renglón original')
    description = models.CharField('Descripción', max_length=500)
    quantity = models.DecimalField('Cantidad', max_digits=12, decimal_places=3, default=1,
        validators=[MinValueValidator(Decimal('0.001'))])
    unit_price = models.DecimalField('Precio unitario', max_digits=17, decimal_places=4,
        validators=[MinValueValidator(Decimal('0'))])

    class Meta:
        ordering = ['id']

    @property
    def amount(self):
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def _check_editable(self):
        parents = {self.invoice_id}
        if self.pk:
            previous_parent = type(self).objects.filter(pk=self.pk).values_list('invoice_id', flat=True).first()
            if previous_parent:
                parents.add(previous_parent)
        if Invoice.objects.filter(pk__in=parents).exclude(status__in=EDITABLE_STATES).exists():
            raise ValidationError('No se pueden modificar las líneas de un comprobante emitido o pendiente.')

    def clean(self):
        super().clean()
        if not self.original_line_id:
            return
        if self.invoice.document_type != 13 or not self.invoice.original_id:
            raise ValidationError({'original_line': 'Solo una nota de crédito asociada puede referenciar un renglón original.'})
        if self.original_line.invoice_id != self.invoice.original_id:
            raise ValidationError({'original_line': 'El renglón no pertenece a la factura asociada.'})
        if self.original_line.original_line_id:
            raise ValidationError({'original_line': 'El renglón original debe pertenecer a una factura, no a otra nota.'})

    def save(self, *args, **kwargs):
        self._check_editable()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._check_editable()
        return super().delete(*args, **kwargs)


class InvoiceAttempt(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='attempts', on_delete=models.PROTECT)
    number = models.PositiveBigIntegerField()
    operation = models.CharField(max_length=12, default='authorize')
    outcome = models.CharField(max_length=12, default='sending')
    request_payload = models.JSONField(default=dict)
    fiscal_context = models.JSONField(default=dict)
    response = models.JSONField(default=dict)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-created_at']


class AccessTicket(models.Model):
    configuration = models.ForeignKey(ArcaConfiguration, on_delete=models.CASCADE)
    fingerprint = models.CharField(max_length=64)
    encrypted_value = models.TextField()
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['configuration', 'fingerprint'], name='billing_ticket_identity_unique')]
