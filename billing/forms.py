from django import forms
from django.forms import inlineformset_factory

from .models import ArcaConfiguration, Customer, Invoice, InvoiceLine, Issuer


class IssuerForm(forms.ModelForm):
    class Meta:
        model = Issuer
        fields = ['name', 'cuit', 'address', 'gross_income', 'activities_since']
        widgets = {'activities_since': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}


class ConfigurationForm(forms.ModelForm):
    class Meta:
        model = ArcaConfiguration
        fields = ['point_of_sale', 'certificate_name', 'private_key_name', 'password_env',
            'timeout', 'generation_offset', 'expiration_window', 'enabled']
        help_texts = {'certificate_name': 'Nombre dentro de la carpeta privada del servidor. Se admiten CRT/PEM o PFX/P12.',
            'private_key_name': 'Necesario para CRT/PEM. Para PFX, dejalo vacío.',
            'password_env': 'Solo el nombre de la variable del servidor. Nunca escribas aquí la contraseña.',
            'enabled': 'Al habilitar, se comprueban el certificado y el punto de venta mediante consultas a ARCA.'}


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'document_type', 'document_number', 'vat_condition', 'address', 'email', 'user', 'active']


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['configuration', 'customer', 'document_type', 'issue_date', 'concept',
            'service_from', 'service_to', 'due_date', 'notes']
        widgets = {field: forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
            for field in ('issue_date', 'service_from', 'service_to', 'due_date')}
        widgets['notes'] = forms.Textarea(attrs={'rows': 2})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['configuration'].queryset = ArcaConfiguration.objects.order_by('environment')
        self.fields['customer'].queryset = Customer.objects.filter(active=True)
        self.fields['document_type'].choices = [(13, 'Nota de crédito C')] if self.instance.original_id else [(11, 'Factura C')]

    def clean(self):
        data = super().clean()
        if data.get('concept') in (2, 3):
            for field in ('service_from', 'service_to', 'due_date'):
                if not data.get(field):
                    self.add_error(field, 'Este dato es obligatorio para servicios.')
            if data.get('service_from') and data.get('service_to') and data['service_from'] > data['service_to']:
                self.add_error('service_to', 'Debe ser igual o posterior al inicio del período.')
            if data.get('due_date') and data.get('issue_date') and data['due_date'] < data['issue_date']:
                self.add_error('due_date', 'Debe ser igual o posterior a la fecha del comprobante.')
        return data


LineFormSet = inlineformset_factory(Invoice, InvoiceLine, fields=['description', 'quantity', 'unit_price'],
    extra=1, min_num=1, validate_min=True, max_num=50, validate_max=True, absolute_max=50, can_delete=True)
