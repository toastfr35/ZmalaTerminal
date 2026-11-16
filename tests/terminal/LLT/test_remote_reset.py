# @test T-LLT-139
# @requirements LLR-TERM-SETUP-033
# @environment portable
# @plan Exercise reset IPC with temporary files and a fake BlueZ adapter. Verify fixed-owner bounded requests, interrupted removal, duplicate suppression, unrelated-device preservation and UI gating until the matching acknowledgement. Actual remote removal requires physical qualification.
# @pass Requests cannot select arbitrary devices; failed cleanup retries the original device; old acknowledgements cannot unblock setup.
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tests.terminal.LLT.test_pi_install import pair
from zmala_terminal.linux import pairing_status


@unittest.skipUnless(os.name == 'posix', 'POSIX pairing service')
class RemoteResetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.request = self.root/'remote-reset.json'
        self.state = self.root/'reset.json'
        for module, name, value in (
                (pair, 'RESET_REQUEST', self.request), (pair, 'RESET_STATE', self.state),
                (pair, 'BOND', self.root/'bond.json'), (pair, 'STATUS', self.root/'status.json'),
                (pairing_status, 'RESET_REQUEST', self.request)):
            started = patch.object(module, name, value)
            started.start()
            self.addCleanup(started.stop)
        self.remote = {'Name': pair.NAME, 'UUIDs': [pair.HID], 'Paired': True, 'Adapter': '/adapter'}
        self.agent = pair.Pairing.__new__(pair.Pairing)
        self.agent.target = None
        self.agent.state = None
        self.agent.call = Mock()
        self.identity = 'a'*32

    def test_removal_resumes_original_target_and_does_not_remove_other_devices(self):
        pair.bond_token('/remote')
        devices = {'/remote': self.remote, '/keyboard': {'Paired': True, 'Adapter': '/adapter'}}
        with patch.object(pair, 'reset_request', return_value=self.identity):
            self.agent.call.side_effect = OSError('BlueZ unavailable')
            with self.assertRaises(OSError):
                self.agent.reset_remote(devices)
            self.assertFalse(pair.reset_state()['done'])
            self.assertTrue(pair.BOND.exists())
            # Simulate a restart after RemoveDevice succeeded but before committing completion.
            devices.pop('/remote')
            devices['/other-presenter'] = self.remote
            self.agent.call.reset_mock(side_effect=True)
            self.assertTrue(self.agent.reset_remote(devices))
            self.agent.call.assert_not_called()
            self.assertFalse(pair.BOND.exists())
            self.assertEqual(self.agent.state, {'state': 'unpaired', 'reset_request': self.identity})
            pair.bond_token('/new')
            self.assertFalse(self.agent.reset_remote(devices))
            self.assertEqual(pair.saved_bond()['device'], '/new')

    def test_removes_only_selected_presenter_and_waits_for_inflight_pair(self):
        pair.bond_token('/remote')
        devices = {'/remote': self.remote, '/other': self.remote}
        with patch.object(pair, 'reset_request', return_value=self.identity):
            self.agent.target = '/new'
            self.assertTrue(self.agent.reset_remote(devices))
            self.agent.call.assert_not_called()
            self.agent.target = None
            self.assertTrue(self.agent.reset_remote(devices))
        self.agent.call.assert_called_once_with('/adapter', 'org.bluez.Adapter1', 'RemoveDevice', '(o)', ('/remote',))

    def test_missing_adapter_cannot_acknowledge_reset(self):
        from tests.terminal.LLT.test_pi_install import PiInstallTests
        agent, bus, glib = PiInstallTests().pairing()
        bus.call_sync.return_value.unpack.return_value = ({},)
        pair.bond_token('/remote')
        with patch.object(pair, 'reset_request', return_value=self.identity):
            self.assertTrue(agent.tick())
        self.assertFalse(self.state.exists())
        self.assertTrue(pair.BOND.exists())
        self.assertNotIn('reset_request', agent.state)

    def test_client_waits_for_matching_acknowledgement_across_restart(self):
        with patch.dict(os.environ, {'ZMALA_PAIRING_STATUS': str(pair.STATUS)}):
            client = pairing_status.PairingStatus()
            client.reset()
            identity = json.loads(self.request.read_text())['request']
            restarted = pairing_status.PairingStatus()
            pair.STATUS.write_text(json.dumps({'state': 'paired', 'bond': 'old', 'reset_request': 'b'*32}))
            self.assertEqual(restarted.read(), 'pairing')
            self.assertIsNone(restarted.bond)
            self.assertTrue(self.request.exists())
            pair.STATUS.write_text(json.dumps({'state': 'unpaired', 'reset_request': identity}))
            restarted.next_read = 0
            self.assertEqual(restarted.read(), 'unpaired')
            self.assertFalse(self.request.exists())

    def test_request_rejects_wrong_owner_permissions_symlink_and_oversize(self):
        import pwd
        self.request.write_text(json.dumps({'schema': 1, 'request': self.identity}))
        self.request.chmod(0o600)
        uid = os.getuid()
        if uid == 0:
            self.skipTest('Test requires an unprivileged user')
        with patch.dict(os.environ, {'ZMALA_USER': pwd.getpwuid(uid).pw_name}):
            self.assertEqual(pair.reset_request(), self.identity)
            with patch('pwd.getpwnam', return_value=Mock(pw_uid=uid+1)):
                self.assertIsNone(pair.reset_request())
            self.request.chmod(0o644)
            self.assertIsNone(pair.reset_request())
            self.request.chmod(0o600)
            self.request.write_text('x'*257)
            self.assertIsNone(pair.reset_request())
            self.request.unlink()
            self.request.symlink_to(pair.STATUS)
            self.assertIsNone(pair.reset_request())
