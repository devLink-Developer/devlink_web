from django.core.management.base import BaseCommand, CommandError
from billing.arca import ArcaClient, certificate_material
from billing.models import ArcaConfiguration


class Command(BaseCommand):
    help = 'Verifica certificado local. --online agrega consultas a ARCA, sin emitir comprobantes.'

    def add_arguments(self, parser):
        parser.add_argument('--environment', choices=['HOMO', 'PROD'], required=True)
        parser.add_argument('--online', action='store_true')

    def handle(self, *args, **options):
        try:
            config = ArcaConfiguration.objects.select_related('issuer').get(environment=options['environment'])
            material = certificate_material(config)
            self.stdout.write(f'Ambiente {config.environment}; certificado {material["serial"]}; vence {material["expires_at"].isoformat()}. Clave y CUIT verificados.')
            if options['online']:
                client = ArcaClient(config)
                self.stdout.write(str(client.status()))
                for point in client.points_of_sale():
                    self.stdout.write(f'PV {point["number"]}; {point["emission_type"]}; bloqueado={point["blocked"]}; baja={point["closed"]}')
        except Exception as exc:
            from django.core.exceptions import ValidationError
            detail = ' '.join(exc.messages) if isinstance(exc, ValidationError) else 'Revisá configuración y conectividad.'
            raise CommandError(detail) from None
