from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from billing.models import Invoice
from billing.services import reconcile_invoice


class Command(BaseCommand):
    help = 'Consulta y concilia comprobantes pendientes; nunca solicita nuevas autorizaciones.'

    def add_arguments(self, parser):
        parser.add_argument('--environment', choices=['HOMO', 'PROD'], required=True)
        parser.add_argument('--user', required=True, help='Superusuario responsable de la operación')
        parser.add_argument('--invoice', help='UUID opcional; por defecto hasta 25 pendientes')

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options['user'], is_active=True, is_superuser=True).first()
        if not user:
            raise CommandError('Indicá un superusuario activo.')
        pending = Invoice.objects.filter(environment=options['environment'], status__in=['sending', 'unknown'])
        if options['invoice']:
            pending = pending.filter(pk=options['invoice'])
        for invoice in list(pending.order_by('created_at')[:25]):
            try:
                result = reconcile_invoice(invoice.pk, user)
                self.stdout.write(f'{result.environment} {result.pk}: {result.status}')
            except Exception:
                self.stderr.write(f'{invoice.environment} {invoice.pk}: no se pudo conciliar; permanece pendiente.')
