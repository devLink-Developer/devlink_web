from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from billing.models import Issuer, ArcaConfiguration


class SetupTests(TestCase):
    def test_setup_is_idempotent_and_does_not_activate_emission(self):
        call_command('billing_setup', stdout=StringIO())
        issuer = Issuer.objects.get()
        issuer.address = 'Domicilio que debe conservarse'
        issuer.save()
        call_command('billing_setup', stdout=StringIO())
        self.assertEqual(Issuer.objects.count(), 1)
        self.assertEqual(Issuer.objects.get().address, 'Domicilio que debe conservarse')
        self.assertEqual(ArcaConfiguration.objects.count(), 2)
        self.assertFalse(ArcaConfiguration.objects.filter(enabled=True).exists())
