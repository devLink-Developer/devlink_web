from django.db import migrations, models
import django.db.models.deletion


def link_unambiguous_credit_lines(apps, schema_editor):
    InvoiceLine = apps.get_model('billing', 'InvoiceLine')
    credit_lines = InvoiceLine.objects.filter(
        invoice__document_type=13,
        invoice__original_id__isnull=False,
        original_line_id__isnull=True,
    ).select_related('invoice')
    for credit_line in credit_lines.iterator():
        candidates = list(InvoiceLine.objects.filter(
            invoice_id=credit_line.invoice.original_id,
            description=credit_line.description,
            unit_price=credit_line.unit_price,
        ).values_list('pk', flat=True)[:2])
        if len(candidates) == 1:
            InvoiceLine.objects.filter(pk=credit_line.pk).update(original_line_id=candidates[0])


class Migration(migrations.Migration):
    dependencies = [('billing', '0003_invoice_source_invoice_source_document_and_more')]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='cancellation_kind',
            field=models.CharField(blank=True, choices=[('total', 'Anulación total'),
                ('partial', 'Anulación parcial')], max_length=7, verbose_name='Alcance de la anulación'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='cancellation_reason',
            field=models.CharField(blank=True, max_length=500, verbose_name='Motivo de la anulación'),
        ),
        migrations.AddField(
            model_name='invoiceline',
            name='original_line',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='credit_lines', to='billing.invoiceline', verbose_name='Renglón original'),
        ),
        migrations.RunPython(link_unambiguous_credit_lines, migrations.RunPython.noop),
    ]
