# @test T-LLT-140
# @requirements LLR-TERM-CONFIG-025
# @environment portable
# @plan Check the exact activation command, credential validation, conditional Settings card and phone and call status tracking.
# @pass Ordinary terminals retain their settings and only explicit evidence records each type of successful check.
import unittest
from unittest.mock import patch

from zmala_terminal.common.local_settings import SettingsDraft
from zmala_terminal.common.provisioning import validate_bootstrap
from zmala_terminal.common.server_activation import activation_available, ACTIVATION_QR


class ServerActivationTest(unittest.TestCase):
    def test_card_only_on_activated_appliance(self):
        self.assertNotIn('server_configuration', SettingsDraft().fields_order)
        fields = SettingsDraft(server_active=True).fields_order
        self.assertEqual(fields[fields.index('maintenance')-1], 'server_configuration')

    def test_activation_requires_exact_code_and_installed_helper(self):
        with patch('zmala_terminal.common.server_activation.HELPER') as helper:
            helper.is_file.return_value = True
            self.assertTrue(activation_available(ACTIVATION_QR))
            self.assertFalse(activation_available(ACTIVATION_QR+' '))
            helper.is_file.return_value = False
            self.assertFalse(activation_available(ACTIVATION_QR))

    def test_phone_check_and_call_confirmation_are_separate_and_origin_scoped(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from zmala_terminal.common.server_page import ServerPage
        with TemporaryDirectory() as directory:
            page = ServerPage(Path(directory))
            page.responses.put(('connected', {'state':'reached', 'origin':'https://one.example', 'checked':100000}))
            self.assertTrue(page.poll(None))
            self.assertTrue(page.when('reached'))
            self.assertFalse(page.when('call'))
            page.remember('call', 200000)
            restored = ServerPage(Path(directory))
            restored.details = dict(page.details)
            self.assertTrue(restored.when('call'))
            restored.details['origin'] = 'https://two.example'
            self.assertFalse(restored.when('call'))
            self.assertFalse(restored.when('reached'))

    def test_invalid_export_fails_before_network_access(self):
        with self.assertRaises(ValueError):
            validate_bootstrap(dict(server_url='http://localhost', device_id='term1', device_token=''))
