# @test T-LLT-037
# @requirements LLR-TERM-POWER-012, LLR-TERM-POWER-013, LLR-TERM-POWER-014, LLR-TERM-POWER-015, LLR-TERM-POWER-016, LLR-TERM-POWER-017, LLR-TERM-MAINT-028
# @environment portable
# @plan Verify either supported USB identity may power down, but unrelated devices cannot. Control time, remote battery, hub status, input, previews and calls with mocked USB helpers. Assert three modes, sixty seconds after media activity ends, no USB activity from navigation, battery boundaries, immediate media wake requests, readiness gating, bounded retries and truthful power indication. Inject applied-volume status and worker time to verify ringing only after nonzero mixer convergence, atomic power telemetry, ringer termination escalation and unconditional shutdown power restoration.
# Verify successful transitions and shutdown are quiet while helper rollback errors
# remain visible; ordinary power-on emits no helper diagnostics. No real USB is switched.
# Root cleanup must skip every USB operation while a trusted trial fence exists;
# reject writable/symlink IPC and preserve the fence after a stale producer.
# @pass All named assertion cases must pass; skips and visual/hardware checks are recorded separately.

"""Boundary, wake-race, stale-input and cancellation tests without powering USB."""
from zmala_terminal.common.callbacks import CallbackController
from zmala_terminal.common.media_adapter import MediaAdapter
from zmala_terminal.linux import media as linux_media
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from zmala_terminal.linux.usb_power import UsbPower, should_power_off
from zmala_terminal.common.call_control import CallControl
from zmala_terminal.common.model import State
from zmala_terminal.common.engine import Engine
from zmala_terminal.common.input_control import InputControl
from zmala_terminal.common.management import ManagementLoop


class UsbPowerTests(unittest.TestCase):
    def setUp(self):
        route = patch('zmala_terminal.linux.usb_power.playback_device', return_value='default:C20')
        route.start()
        self.addCleanup(route.stop)

    def test_power_worker_status_and_ringer_wait_for_applied_nonzero_volume(self):
        import zmala_terminal.linux.usb_power as module
        power = self.controller()
        power.state, power.powered, power.ringing = 'on', True, True
        power.revision = power.refreshed = 2
        power.command = Mock()
        samples = iter([(50, None, False), (0, 0, False), (40, 40, False), (40, 40, True)])
        power.tone_levels = Mock()
        power.tone_levels.prepare.return_value=Path('/runtime/tone.wav')
        clock = [1000]
        snapshots = []
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', {'ZMALA_RUNTIME_DIR': folder}), \
                patch.object(module.time, 'monotonic', side_effect=lambda: clock[0]), \
                patch('zmala_terminal.linux.c20_volume.status', side_effect=lambda: next(samples)), \
                patch.object(module.subprocess, 'Popen') as popen:
            process = popen.return_value
            process.poll.return_value = None
            def wait(_):
                snapshots.append(popen.call_count)
                clock[0] += 5
                if len(snapshots) == 4:
                    power.stopped = True
            power.changed = Mock(wait=Mock(side_effect=wait))
            power.run()
            self.assertEqual(snapshots, [0, 1, 1, 1])
            self.assertIn('default:C20', popen.call_args.args[0])
            self.assertEqual(process.terminate.call_count, 1)
            import json
            state = json.loads((Path(folder)/'usb-power.json').read_text())
            self.assertEqual((state['state'], state['powered']), ('on', True))
            self.assertFalse((Path(folder)/'usb-power.tmp').exists())
        power.command.assert_called_once_with('on')

    def test_ringer_stop_timeout_kills_and_worker_shutdown_restores_power(self):
        import zmala_terminal.linux.usb_power as module
        power = self.controller()
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = module.subprocess.TimeoutExpired('aplay', .3)
        power.ringer = process
        power.close()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertIsNone(power.ringer)
        self.assertTrue(power.changed.is_set())
        with patch.object(power, 'command', side_effect=OSError('hub gone')) as command, \
                patch.object(module.logging, 'exception') as logged:
            power.run()
        command.assert_called_once_with('on')
        logged.assert_called_once()
        with patch.object(module.subprocess, 'run') as run:
            power.command('on')
            power.command('off')
        for request, action, budget in zip(run.call_args_list, ('on', 'off'), (48, 101)):
            self.assertEqual(request.args[0], ['sudo', '-n', module.HELPER, action])
            self.assertGreater(request.kwargs['timeout'], budget)

    def test_media_reenumeration_requires_c20_video_and_alsa_and_handles_disconnect(self):
        import zmala_terminal.linux.usb_power as module
        video = Mock()
        video.resolve.return_value = '/sys/devices/usb1/1-1.2/video4linux/video0'
        video.__truediv__ = Mock(return_value=SimpleNamespace(read_text=lambda: 'Nuroum C20'))
        audio = Mock()
        audio.read_text.return_value = 'C20\n'
        with patch.object(module, 'Path') as path:
            path.side_effect = lambda name: SimpleNamespace(glob=lambda pattern: [video] if 'video' in name else [audio])
            self.assertTrue(module.media_present())
            audio.read_text.return_value = 'HDMI'
            self.assertFalse(module.media_present())
            audio.read_text.side_effect = OSError('gone')
            self.assertFalse(module.media_present())
        with patch.object(module.sys, 'platform', 'linux'), patch.dict('os.environ', {'ZMALA_USB_POWER': '1'}), \
                patch.object(module.threading, 'Thread') as thread:
            enabled = module.UsbPower(Path('.'))
        self.assertEqual(enabled.state, 'starting')
        thread.return_value.start.assert_called_once()

    def test_successful_transitions_and_shutdown_are_quiet(self):
        for previous in ('starting', 'off', 'error', 'on'):
            power = self.controller(); power.state = previous
            power.active = previous != 'on'
            power.battery = 95; power.updated = 1000; power.last_use = 0
            def command(action):
                power.stopped = True
            power.command = Mock(side_effect=command)
            with patch('time.monotonic', return_value=1000), \
                    patch('zmala_terminal.linux.usb_power.media_present', return_value=True), \
                    self.assertNoLogs(level='INFO'):
                power.run()
            self.assertEqual(power.command.call_args_list,
                             [unittest.mock.call('off' if previous == 'on' else 'on'), unittest.mock.call('on')])

    def test_helper_rollback_output_survives_subprocess_capture(self):
        import subprocess
        power = self.controller()
        with patch('zmala_terminal.linux.usb_power.subprocess.run', side_effect=
                   subprocess.CalledProcessError(1, 'helper', stderr='USB power-off failed; restoring power')), \
                self.assertLogs(level='WARNING') as logs:
            with self.assertRaises(subprocess.CalledProcessError): power.command('off')
        self.assertIn('power-off failed; restoring power', logs.output[0])

    def test_exact_idle_and_battery_boundaries(self):
        self.assertFalse(should_power_off(59.9, 0, False, 100, 'camera'))
        self.assertFalse(should_power_off(59.9, 0, False, 100, 'camera_and_dock'))
        self.assertTrue(should_power_off(60, 0, False, 25, 'camera_and_dock'))
        self.assertFalse(should_power_off(900, 0, False, 100, 'always_on'))
        for battery in (None, 24, 0, True, 101, '100'):
            self.assertFalse(should_power_off(900, 0, False, battery, 'camera_and_dock'))
            self.assertTrue(should_power_off(60, 0, False, battery, 'camera'))
        self.assertFalse(should_power_off(900, 0, True, 100, 'camera'))

    def controller(self):
        with patch.dict('os.environ', {}, clear=True):
            power = UsbPower(Path('.'))
        power.enabled = True
        power.mode = 'camera_and_dock'
        return power

    def test_input_does_not_wake_usb_or_reset_media_idle_time(self):
        app = InputControl()
        app.usb_power = self.controller()
        app.usb_power.state = 'off'
        app.usb_power.last_use = 900
        app.remote_setup_blocked = lambda: True
        app.setup_stage = 'remote'
        for action in (lambda: app.keypress('red'), lambda: app.pointer_button(True), app.volume_activity):
            app.usb_power.active = False
            app.usb_power.changed.clear()
            with patch('time.monotonic', return_value=1000):
                action()
            self.assertEqual(app.last_button, 1000)
            self.assertEqual(app.usb_power.last_use, 900)
            self.assertEqual(app.usb_power.wake_serial, 0)
            self.assertFalse(app.usb_power.changed.is_set())
        app.usb_power.set_mode('camera')
        self.assertTrue(should_power_off(1000, app.usb_power.last_use, False, 95, 'camera'))

    def test_idle_starts_after_activity_ends(self):
        power = self.controller()
        with patch('time.monotonic', return_value=1000):
            power.update(False, 95)
        self.assertEqual(power.last_use, 1000)
        with patch('time.monotonic', return_value=1100):
            power.update(False, 95)
        self.assertEqual(power.last_use, 1000)

    def test_preview_wakes_usb_until_it_ends_even_with_settings_left_open(self):
        app = ManagementLoop(); app.callbacks = CallbackController()
        power = app.usb_power = self.controller()
        power.mode = 'camera'; power.state = 'off'; power.active = False; power.last_use = 0
        app.setup_stage = app.scanner = app.engine = None
        app.model = Mock(state=State.HOME, config={'usb_power': 'camera'})
        app.settings_open = True
        app.keys_down = {'red'}
        app.presenter_input = Mock(battery=95)
        with patch('time.monotonic', return_value=1000):
            power.set_ringtone('test.wav', 0)
            power.preview_tone('test.wav')
            app.tick_usb()
            self.assertEqual(power.ringtone_preview_status, 'muted')
            self.assertEqual(power.wake_serial, 0)
            self.assertEqual(power.last_use, 0)
            self.assertFalse(power.active)
            power.set_ringtone('test.wav', 50)
            power.preview_tone('test.wav')
            self.assertEqual(power.wake_serial, 1)
            app.tick_usb()
            self.assertTrue(power.active)
        with patch('time.monotonic', return_value=1010):
            power.stop_preview()
            app.tick_usb()
        self.assertEqual(power.last_use, 1010)
        self.assertFalse(power.active)
        self.assertFalse(should_power_off(1069.9, power.last_use, power.active, power.battery, power.mode))
        self.assertTrue(should_power_off(1070, power.last_use, power.active, power.battery, power.mode))

    def test_incoming_call_wakes_before_tv_work(self):
        app = CallControl(); app.callbacks = CallbackController()
        app.setup_stage = None
        app.model, app.engine, app.root = Mock(), Mock(), Mock()
        app.render = Mock()
        app.usb_power = self.controller()
        app.tv_control = Mock()
        def check_woken(*, ringing):
            self.assertTrue(callable(ringing))
            self.assertEqual(app.usb_power.wake_serial, 1)
            self.assertTrue(app.usb_power.changed.is_set())
        app.tv_control.wake.side_effect = check_woken
        app.call_event(123, 1, 'term1', 'example.test')
        app.tv_control.wake.assert_called_once()

    def test_failed_off_restores_without_waiting_for_input(self):
        power = self.controller()
        power.active, power.battery = False, 95
        power.last_use, power.updated = 0, 1000
        power.state = 'on'
        actions = []
        def command(action):
            actions.append(action)
            if action == 'off':
                raise RuntimeError('off interrupted')
            power.stopped = True
        power.command = command
        with patch('time.monotonic', return_value=1000), patch('zmala_terminal.linux.usb_power.media_present', return_value=True):
            power.run()
        self.assertEqual(actions[:2], ['off', 'on'])
        self.assertTrue(power.power_state)
        self.assertEqual(power.last_use, 1000)

    def test_confirmed_supply_is_independent_of_missing_camera(self):
        power = self.controller()
        power.state = 'off'
        def command(action):
            power.stopped = True
        power.command = command
        with patch('zmala_terminal.linux.usb_power.media_present', return_value=False):
            power.run()
        self.assertTrue(power.power_state)
        self.assertFalse(power.ready)

    def test_wake_is_not_ready_until_native_devices_refreshed(self):
        power = self.controller()
        power.state, power.revision = 'on', 1
        self.assertFalse(power.require())
        engine = Mock()
        power.refresh(engine)
        engine.refresh_usb_devices.assert_called_once()
        self.assertTrue(power.ready)

    def test_off_transition_cannot_be_treated_as_ready(self):
        power = self.controller()
        power.state = 'switching'
        self.assertFalse(power.require())
        self.assertTrue(power.active)

    def test_running_media_defers_refresh(self):
        power = self.controller()
        power.state, power.revision = 'on', 1
        engine = Mock()
        engine.refresh_usb_devices.return_value = False
        power.refresh(engine)
        self.assertFalse(power.ready)

    def test_udev_settling_does_not_break_ui_tick_or_spin(self):
        power = self.controller()
        power.state, power.revision = 'on', 1
        engine = Mock()
        engine.refresh_usb_devices.side_effect = [RuntimeError('C20 unavailable'), None]
        with patch('zmala_terminal.linux.usb_power.time.monotonic', return_value=10):
            power.refresh(engine)
            power.refresh(engine)
        self.assertFalse(power.ready)
        engine.refresh_usb_devices.assert_called_once()
        with patch('zmala_terminal.linux.usb_power.time.monotonic', return_value=11):
            power.refresh(engine)
        self.assertTrue(power.ready)

    def test_stalled_ui_restores_power(self):
        power = self.controller()
        power.active, power.battery = False, 100
        power.updated = power.last_use = 0
        power.state = 'off'
        actions = []
        def command(action):
            actions.append(action)
            power.stopped = True
        power.command = command
        with patch('zmala_terminal.linux.usb_power.media_present', return_value=True):
            power.run()
        self.assertTrue(actions)
        self.assertEqual(set(actions), {'on'})

    def test_cancelled_answer_does_not_run_after_wake(self):
        app = CallControl(); app.callbacks = CallbackController()
        app.engine, app.root, app.model = Mock(), Mock(), Mock()
        app.usb_media_ready, app.action = Mock(return_value=False), Mock()
        app.engine.call = 123
        app.generation = 5
        app.closed = False
        app.model.state = State.CONNECTING
        app.usb_media_ready.return_value = False
        CallControl.action(app, 'answer')
        callback = app.root.after.call_args.args[1]
        app.model.state = State.HOME
        callback()
        app.engine.answer.assert_not_called()
        app.action.assert_not_called()

    def test_disabled_on_desktop(self):
        with patch.dict('os.environ', {}, clear=True):
            power = UsbPower(Path('.'))
        self.assertFalse(power.enabled)
        self.assertTrue(power.require())

    def test_zero_volume_mutes_and_remote_increase_unmutes(self):
        engine = Engine.__new__(Engine); engine.media = MediaAdapter(linux_media)
        engine.core = 123
        engine.core_set_playback_gain_db = Mock()
        with patch('zmala_terminal.common.engine.WINDOWS', False), patch('zmala_terminal.linux.c20_volume.status',
                side_effect=[(0, 0, False), (0, 0, False), (2, 2, False)]):
            for _ in range(3):
                engine.sync_speaker_mute()
        self.assertEqual([call.args for call in engine.core_set_playback_gain_db.call_args_list],
                         [(123, -120), (123, -16.8)])


class HelperSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[3] / 'build_tools/linux/usb-power.py'
        spec = importlib.util.spec_from_file_location('usb_helper', path)
        cls.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.helper)

    def test_cleanup_restore_honors_maintenance_before_device_io(self):
        h=self.helper
        with patch.object(h.os,'geteuid',return_value=0,create=True), patch.object(h,'maintenance_active',return_value=True), \
                patch.object(h,'validate_board') as board,patch.object(h,'switch') as switch:
            h.power('restore');board.assert_not_called();switch.assert_not_called()
        with patch.object(h.os,'geteuid',return_value=0,create=True), patch.object(h,'maintenance_active',return_value=False), \
                patch.object(h,'validate_board'),patch.object(h,'switch') as switch:
            h.power('restore');switch.assert_called_once_with('on')
        with patch.object(h.os,'geteuid',return_value=1000,create=True):
            with self.assertRaises(PermissionError):h.power('restore')

    @unittest.skipUnless(os.name=='posix','Root-owned no-follow maintenance IPC')
    def test_cleanup_fence_requires_bounded_trusted_state_and_retains_stale_trial(self):
        h=self.helper
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request'
            value={'phase':'checking','nonce':'a'*32,'heartbeat':0}
            path.write_text(json.dumps(value));path.chmod(0o644)
            self.assertTrue(h.maintenance_active(path,os.getuid()))
            for phase in ('idle','request','unknown'):
                value['phase']=phase;path.write_text(json.dumps(value))
                self.assertFalse(h.maintenance_active(path,os.getuid()))
            value['phase']='checking';path.write_text(json.dumps(value));path.chmod(0o666)
            self.assertFalse(h.maintenance_active(path,os.getuid()))
            path.unlink();path.symlink_to(Path(directory)/'absent')
            self.assertFalse(h.maintenance_active(path,os.getuid()))

    def test_helper_inventory_checks_board_hub_topology_and_keeps_external_hubs(self):
        h = self.helper
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'USB', Path(directory)), \
                patch.object(h.Path, 'read_bytes', return_value=b'Raspberry Pi 4 Model B Rev 1.5'):
            root = Path(directory)
            for name, vendor, product, kind in [('1-1','2109','3431','09'), ('usb2','1d6b','0003','09'),
                                                ('1-1.2','0525','a4ad','ef'), ('1-1.3','abcd','1234','09')]:
                device = root/name; device.mkdir()
                for field, value in [('idVendor',vendor),('idProduct',product),('bDeviceClass',kind)]:
                    (device/field).write_text(value)
            (root/'interface').mkdir()
            h.validate_board()
            self.assertCountEqual(h.devices(), [(root/'1-1.2', ('0525','a4ad')), (root/'1-1.3', ('abcd','1234'))])
            (root/'usb2/idProduct').write_text('other')
            with self.assertRaisesRegex(RuntimeError, 'topology'):
                h.validate_board()
        with patch.object(h.Path, 'read_bytes', return_value=b'Raspberry Pi 3 Model B'):
            with self.assertRaisesRegex(RuntimeError, 'Pi 4'):
                h.validate_board()
        with patch.object(h.subprocess, 'run', return_value='ok') as run:
            self.assertEqual(h.run('unit-command'), 'ok')
            run.assert_called_once_with(('unit-command',), check=True, capture_output=True, text=True, timeout=12)

    def test_helper_on_needs_no_camera_and_off_requires_exactly_one_idle_camera(self):
        h = self.helper
        with patch.object(h, 'validate_board'), patch.object(h, 'devices', return_value=[]), \
                patch.object(h, 'switch') as switch, patch.object(h.sys, 'stderr') as stderr:
            h.power('on'); switch.assert_called_once_with('on')
            stderr.write.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, 'exactly one'):
                h.power('off')
        with tempfile.TemporaryDirectory() as directory, patch.object(h, 'validate_board'), \
                patch.object(h.Path, 'glob', return_value=[Path('/dev/video0')]), \
                patch.object(h.subprocess, 'run', return_value=Mock(returncode=1)) as opened, patch.object(h, 'switch') as switch:
            camera = Path(directory); (camera/'authorized').write_text('1')
            def check_off(action):
                self.assertEqual(action, 'off')
                self.assertEqual((camera/'authorized').read_text(), '0')
            switch.side_effect = check_off
            for product in ('a4ad', 'a4b0'):
                (camera/'authorized').write_text('1')
                with patch.object(h, 'devices', return_value=[(camera, ('0525',product))]):
                    h.power('off')
            self.assertEqual(switch.call_count, 2)
            self.assertEqual(opened.call_args.kwargs['timeout'], 5)

    def test_successful_command_with_unchanged_ports_is_rejected(self):
        output = '\n'.join(f'  Port {i}: 0000 off' for i in range(1, 5))
        with patch.object(self.helper, 'run', return_value=Mock(stdout=output)):
            with self.assertRaisesRegex(RuntimeError, 'did not confirm'):
                self.helper.switch('on')

    def test_both_hubs_confirm_power(self):
        for action, usb2, usb3 in [('on', '0507 power highspeed enable connect', '02a0 power'),
                                  ('off', '0000', '0080 off'),
                                  ('off', '0200 low speed', '0100 off')]:
            statuses = [Mock(stdout='\n'.join(f'  Port {i}: {state}' for i in range(1, 5)))
                        for state in (usb2, usb3)]
            with patch.object(self.helper, 'run', side_effect=[None, statuses[0], None, statuses[1]]) as run:
                self.helper.switch(action)
                self.assertEqual(run.call_count, 4)

    def test_failed_usb2_power_on_still_attempts_usb3(self):
        usb3 = '\n'.join(f'  Port {i}: 0200 power' for i in range(1, 5))
        with patch.object(self.helper, 'run', side_effect=[OSError('USB 2 error'), None, Mock(stdout=usb3)]) as run:
            with self.assertRaisesRegex(RuntimeError, 'USB 2 error'):
                self.helper.switch('on')
            self.assertEqual(run.call_args_list[1].args[-4:], ('-l', '2', '-a', 'on'))

    def test_unknown_peripheral_blocks_shared_power_off(self):
        h = self.helper
        with patch.object(h, 'validate_board'), patch.object(h, 'devices', return_value=[(Path('/fake'), ('1234','5678'))]), patch.object(h, 'switch') as switch:
            with self.assertRaisesRegex(RuntimeError, 'Other USB'):
                h.power('off')
            switch.assert_not_called()

    def test_failed_power_off_restores_supply_and_authorization(self):
        h = self.helper
        with tempfile.TemporaryDirectory() as tmp:
            camera = Path(tmp)
            (camera / 'authorized').write_text('1')
            with patch.object(h, 'validate_board'), patch.object(h, 'devices', return_value=[(camera, ('0525','a4ad'))]), patch.object(h.Path, 'glob', return_value=[]), patch.object(h, 'switch', side_effect=[OSError('hub'), None]) as switch:
                with self.assertRaises(OSError):
                    h.power('off')
                self.assertEqual([c.args[0] for c in switch.call_args_list], ['off', 'on'])
                self.assertEqual((camera / 'authorized').read_text(), '1')

    def test_open_media_blocks_power_off(self):
        h = self.helper
        with patch.object(h, 'validate_board'), patch.object(h, 'devices', return_value=[(Path('/fake'), ('0525','a4ad'))]), patch.object(h.Path, 'glob', return_value=[Path('/dev/video0')]), patch.object(h.subprocess, 'run', return_value=Mock(returncode=0)), patch.object(h, 'switch') as switch:
            with self.assertRaisesRegex(RuntimeError, 'still open'):
                h.power('off')
            switch.assert_not_called()

    def test_open_hdmi_does_not_block_usb_power_off(self):
        helper = self.helper
        hdmi = Path('/dev/snd/pcmC2D0p')
        capture = Path('/dev/snd/pcmC3D0c')
        hdmi_driver = Path('../../../../bus/platform/drivers/vc4_hdmi')
        with patch.object(helper.Path, 'read_text', return_value='vc4hdmi1\n'), \
                patch.object(helper.Path, 'readlink', return_value=hdmi_driver) as driver:
            self.assertTrue(helper.onboard_hdmi_pcm(hdmi))
            self.assertFalse(helper.onboard_hdmi_pcm(capture))
            driver.return_value = Path('../../../../bus/usb/drivers/snd-usb-audio')
            self.assertFalse(helper.onboard_hdmi_pcm(hdmi))
            driver.side_effect = FileNotFoundError
            self.assertFalse(helper.onboard_hdmi_pcm(hdmi))

        with tempfile.TemporaryDirectory() as folder:
            camera = Path(folder)
            (camera / 'authorized').write_text('1')
            with patch.object(helper, 'validate_board'), \
                    patch.object(helper, 'devices', return_value=[(camera, ('0525','a4b0'))]), \
                    patch.object(helper, 'onboard_hdmi_pcm', side_effect=lambda node: node == hdmi), \
                    patch.object(helper.Path, 'glob', side_effect=[[], [hdmi, capture]]), \
                    patch.object(helper.subprocess, 'run', return_value=Mock(returncode=1)) as opened, \
                    patch.object(helper, 'switch') as switch:
                helper.power('off')
                opened.assert_called_once_with(['/usr/bin/fuser', str(capture)], capture_output=True, timeout=5)
                switch.assert_called_once_with('off')
                self.assertEqual((camera / 'authorized').read_text(), '0')


if __name__ == '__main__':
    unittest.main()
