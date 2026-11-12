import json
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from billing.importing import import_historical_invoice


class Command(BaseCommand):
    help = 'Registra una factura C existente desde un manifiesto verificado y su PDF original. No llama a ARCA.'

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True)
        parser.add_argument('--pdf', required=True)
        parser.add_argument('--user', required=True)
        parser.add_argument('--update-issuer', action='store_true', help='Actualizar datos actuales del emisor con los del comprobante')

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(username=options['user'], is_active=True, is_superuser=True).first()
        if not user:
            raise CommandError('Indicá un superusuario activo responsable de la importación.')
        try:
            manifest_path, pdf_path = Path(options['manifest']), Path(options['pdf'])
            if manifest_path.stat().st_size > 128*1024 or pdf_path.stat().st_size > 10*1024*1024:
                raise CommandError('Los archivos superan los tamaños permitidos.')
            invoice = import_historical_invoice(json.loads(manifest_path.read_text(encoding='utf-8-sig')),
                pdf_path.read_bytes(), user, update_issuer=options['update_issuer'])
        except Exception as exc:
            from django.core.exceptions import ValidationError
            detail = ' '.join(exc.messages) if isinstance(exc, ValidationError) else 'Revisá las rutas, el manifiesto y el PDF.'
            raise CommandError(detail) from None
        self.stdout.write(self.style.SUCCESS(f'Registrado: {invoice.get_document_type_display()} {invoice.fiscal_number}; total {invoice.total}; sin emitir otro comprobante. UUID {invoice.pk}'))
