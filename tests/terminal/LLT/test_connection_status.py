# @test T-LLT-110
# @requirements LLR-TERM-NET-005
# @environment portable
# @plan Drive a monotonic clock across startup, the exact 60-second timeout, recovery and a subsequent outage. Vary Wi-Fi independently; test local developer shell active/inactive and probe failure without opening a tunnel.
# @pass Grace is not extended by repeated observations; each recovery resets the timer. Local shell observations never use remote credentials.
import subprocess
import unittest
from unittest.mock import Mock, patch
from zmala_terminal.common.connection_status import ConnectionStatus
from zmala_terminal.linux import developer_access


class ConnectionStatusTests(unittest.TestCase):
    def test_boot_timeout_recovery_and_second_outage(self):
        status = ConnectionStatus()
        self.assertEqual(status.observe(0, False, True), ('connection_connecting', 'amber'))
        self.assertEqual(status.observe(59.99, False, None), ('connection_connecting', 'amber'))
        self.assertEqual(status.observe(60, False, True), ('connection_retrying', 'red'))
        self.assertEqual(status.observe(70, True, False), ('connection_connected', 'green'))
        self.assertEqual(status.observe(80, False, True), ('connection_reconnecting', 'amber'))
        self.assertEqual(status.observe(139.99, False, True), ('connection_reconnecting', 'amber'))
        self.assertEqual(status.observe(140, False, True), ('connection_retrying', 'red'))
        self.assertEqual(status.observe(141, True, True), ('connection_connected', 'green'))

    def test_wifi_wait_does_not_extend_deadline(self):
        status = ConnectionStatus()
        self.assertEqual(status.observe(10, False, False), ('connection_wifi', 'amber'))
        self.assertEqual(status.observe(70, False, False), ('connection_wifi', 'red'))
        self.assertEqual(status.observe(71, False, True), ('connection_retrying', 'red'))

    def test_local_shell_probe(self):
        with patch.object(developer_access.sys, 'platform', 'linux'), patch.object(developer_access.subprocess, 'run') as run:
            for code, expected in [(0, True), (3, False), (4, False), (1, None)]:
                run.return_value = Mock(returncode=code)
                self.assertIs(developer_access.enabled(), expected)
                self.assertEqual(run.call_args.args[0], ['systemctl', 'is-active', '--quiet', 'zmalacall-developer-shell.service'])
            for error in [OSError(), subprocess.TimeoutExpired('systemctl', 2)]:
                run.side_effect = error
                self.assertIsNone(developer_access.enabled())
        with patch.object(developer_access.sys, 'platform', 'win32'), patch.object(developer_access.subprocess, 'run') as run:
            self.assertFalse(developer_access.enabled())
            run.assert_not_called()
