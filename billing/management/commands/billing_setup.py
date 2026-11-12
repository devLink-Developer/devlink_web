from django.core.management.base import BaseCommand
from django.db import transaction
from billing.models import ArcaConfiguration, Issuer


class Command(BaseCommand):
    help = 'Inicializa el emisor propio y ambientes deshabilitados. No llama a ARCA.'

    def handle(self, *args, **options):
        with transaction.atomic():
            issuer, _ = Issuer.objects.get_or_create(pk=1)
            for environment in ('HOMO', 'PROD'):
                ArcaConfiguration.objects.get_or_create(environment=environment, defaults={'issuer': issuer})
        self.stdout.write('Emisor y ambientes disponibles. Completá configuración fiscal; no se habilitó ninguna emisión.')
