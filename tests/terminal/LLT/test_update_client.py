# @test T-LLT-095
# @requirements LLR-TERM-MAINT-028
# @environment portable
# @plan Use temporary local IPC and deterministic clocks to grant/defer/expire leases and retain trial fencing; test malformed/symlink requests, passive-state release and call/input/native-media guards.
# @pass Only eligible current requests are acknowledged; maintenance blocks call/input wake paths and passive startup avoids media settings/volume work. POSIX IPC cases skip on Windows.
# Exercise manual TV lease release under a busy transport and active call, matching
# late rejection, fresh-offer retry and older owners that continue waiting.
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
from zmala_terminal.common.update_client import UpdateClient, tick_terminal
from zmala_terminal.common.call_control import CallControl
from zmala_terminal.common.input_control import InputControl
from zmala_terminal.common.engine import Engine

class UpdateClientTests(unittest.TestCase):
    def test_late_rejection_waits_for_call_to_end_and_install_clears_pending_result(self):
        from zmala_terminal.common.settings_control import SettingsControl
        from zmala_terminal.common.model import State
        menu = Mock(state='error')
        menu.poll.return_value = False
        app = SimpleNamespace(update_client=SimpleNamespace(locked=False, current={}),
            settings_draft=SimpleNamespace(updates=None), pending_update_menu=menu,
            model=SimpleNamespace(state=State.IN_CALL), setup_stage=None,
            engine=SimpleNamespace(call=object()), settings_open=False, render=Mock())
        SettingsControl.tick_settings_updates(app)
        self.assertFalse(app.settings_open)
        self.assertIs(app.pending_update_menu, menu)
        app.model.state, app.engine.call = State.HOME, None
        SettingsControl.tick_settings_updates(app)
        self.assertTrue(app.settings_open)
        self.assertIs(app.settings_draft.updates, menu)
        app.pending_update_menu = menu
        app.update_client.locked = True
        app.update_client.current = {'phase':'updating'}
        SettingsControl.tick_settings_updates(app)
        self.assertIsNone(app.pending_update_menu)

    def test_manual_handover_releases_idle_tv_but_never_during_call(self):
        from zmala_terminal.common.model import State
        from zmala_terminal.linux.tv_control import TVControl
        tv = TVControl(device='/fixture/missing')
        tv.session.browsing = {'address': '1.0.0.0'}
        client = SimpleNamespace(passive=False, tick=Mock(), current={'phase': 'request', 'immediate': True, 'heartbeat': 99})
        app = SimpleNamespace(update_client=client, model=SimpleNamespace(state=State.HOME),
            engine=SimpleNamespace(call=object()), setup_stage=None, settings_open=False, setup_busy=False,
            settings_draft=SimpleNamespace(busy=False), keys_down=set(), last_button=99,
            language='en', closed=False, tv_control=tv)
        tick_terminal(app, 100)
        self.assertIn('call', client.blockers)
        self.assertIsNotNone(tv.session.browsing)
        app.engine.call = None
        tv._lock.acquire()
        try:
            tick_terminal(app, 100)
            self.assertIn('tv', client.blockers)
            self.assertIsNotNone(tv.session.browsing)
        finally:
            tv._lock.release()
        tick_terminal(app, 100)
        self.assertTrue(client.tick.call_args.args[0])
        self.assertIsNone(tv.session.browsing)
        self.assertTrue(tv._cancel.is_set())

    def test_queued_menu_observes_rejection_and_rechecks_before_retry(self):
        from zmala_terminal.common import update_menu
        menu = update_menu.UpdateMenu(offer=Path('/missing/offer'), clock=lambda: 100)
        menu.state, menu.identity, menu.deadline = 'queued', 'a'*32, 130
        with patch.object(update_menu, 'read_record', return_value={
                'schema': 1, 'request': menu.identity, 'state': 'error', 'blockers': ['usb', 'untrusted']}):
            self.assertTrue(menu.poll())
        self.assertEqual(menu.state, 'error')
        self.assertEqual(menu.blockers, ['usb'])
        menu.send = Mock()
        self.assertTrue(menu.apply())
        menu.send.assert_called_once_with('check')
        self.assertEqual(menu.state, 'checking')

    def test_old_owner_waiting_is_not_reported_as_cancelled_and_late_error_is_read(self):
        from zmala_terminal.common import update_menu
        now = [100]
        menu = update_menu.UpdateMenu(offer=Path('/missing/offer'), clock=lambda: now[0])
        menu.state, menu.identity, menu.deadline = 'queued', 'a'*32, 99
        reply = {'schema': 1, 'request': menu.identity, 'state': 'queued'}
        with patch.object(update_menu, 'read_record', side_effect=lambda *args: reply):
            self.assertTrue(menu.poll())
            self.assertEqual(menu.state, 'waiting')
            self.assertFalse(menu.apply())
            now[0] += 1
            reply['state'] = 'error'
            self.assertTrue(menu.poll())
            self.assertEqual(menu.state, 'error')

    @unittest.skipUnless(os.name == 'posix', 'POSIX no-follow IPC')
    def test_manual_apply_uses_only_the_matching_offer(self):
        from zmala_terminal.common import update_menu
        with tempfile.TemporaryDirectory() as directory:
            offer, command = (Path(directory)/name for name in ('offer.json', 'command.json'))
            now = [100]
            offer.write_text('{"schema":1,"state":"current"}')
            read = update_menu.read_record
            with patch.object(update_menu, 'read_record', side_effect=lambda path, uid: read(path, os.getuid())):
                menu = update_menu.UpdateMenu(offer, command, lambda: now[0])
                self.assertFalse(menu.apply())
                first = json.loads(command.read_text())
                self.assertEqual(first['action'], 'check')
                result = {'schema': 1, 'request': 'a'*32, 'state': 'available', 'version': '0.4.4', 'release': 'b'*64}
                offer.write_text(json.dumps(result))
                self.assertFalse(menu.poll())
                now[0] += 1
                result['request'] = first['request']
                offer.write_text(json.dumps(result))
                self.assertTrue(menu.poll())
                self.assertTrue(menu.apply())
                second = json.loads(command.read_text())
                self.assertNotEqual(first['request'], second['request'])
                self.assertEqual((second['action'], second['release']), ('apply', result['release']))

    def test_immediate_lease_still_waits_for_call_and_freshness(self):
        from zmala_terminal.common.model import State
        client = SimpleNamespace(passive=False, tick=Mock(), current={'phase': 'request', 'immediate': True, 'heartbeat': 99})
        app = SimpleNamespace(update_client=client, model=SimpleNamespace(state=State.HOME),
            engine=SimpleNamespace(call=None), setup_stage=None, settings_open=False, setup_busy=False,
            settings_draft=SimpleNamespace(busy=False), keys_down=set(), last_button=99,
            language='en', closed=False)
        tick_terminal(app, 100)
        self.assertTrue(client.tick.call_args.args[0])
        app.engine.call = object()
        tick_terminal(app, 101)
        self.assertFalse(client.tick.call_args.args[0])
        app.engine.call = None
        tick_terminal(app, 110)
        self.assertFalse(client.tick.call_args.args[0])

    def test_failed_ui_cycle_does_not_publish_ready_heartbeat(self):
        from zmala_terminal.common.management import ManagementLoop
        from zmala_terminal.common.model import State
        app=Mock(closed=False,engine=None,configuration=None,shared_photo=None,
                 carousel_motion=None,model=SimpleNamespace(state=State.HOME),
                 update_client=SimpleNamespace(locked=True))
        app.update_timers.side_effect=RuntimeError('broken UI cycle')
        with patch('zmala_terminal.common.update_client.tick_terminal') as heartbeat:
            with self.assertLogs(level='ERROR'):
                ManagementLoop.tick(app)
            heartbeat.assert_not_called()
            app.update_timers.side_effect=None
            ManagementLoop.tick(app)
            heartbeat.assert_called_once()

    def test_passive_poll_cannot_resume_usb_before_real_activity(self):
        from zmala_terminal.common.management import ManagementLoop
        app=SimpleNamespace(update_client=SimpleNamespace(locked=False,passive=True),
                            usb_power=Mock(deferred=True), c20_status=Mock())
        app.c20_status.read.return_value = False
        ManagementLoop.tick_usb(app)
        app.usb_power.resume.assert_not_called()
        app.usb_power.update.assert_not_called()
        app.usb_power.refresh.assert_not_called()

    def test_idle_boot_reconciles_camera_that_is_already_awake(self):
        from zmala_terminal.common.management import ManagementLoop
        from zmala_terminal.common.model import State
        power = Mock(enabled=True, deferred=True, ringtone_preview_status='', playback_active=False)
        client = SimpleNamespace(locked=True, passive=True)
        app = SimpleNamespace(update_client=client, usb_power=power, c20_status=Mock(),
            model=SimpleNamespace(config={'usb_power': 'camera'}, state=State.HOME),
            setup_stage=None, scanner=None, engine=SimpleNamespace(call=None),
            presenter_input=SimpleNamespace(battery=75))
        app.c20_status.read.return_value = True
        ManagementLoop.tick_usb(app)
        app.c20_status.read.assert_not_called()
        power.resume.assert_not_called()

        client.locked = False
        ManagementLoop.tick_usb(app)
        power.resume.assert_called_once()
        power.set_mode.assert_called_once_with('camera')
        power.update.assert_called_once_with(False, 75, False)
        power.refresh.assert_not_called()
        self.assertTrue(client.passive)

    def test_deferred_sleep_is_reported_before_usb_state_is_known(self):
        from zmala_terminal.common.model import State
        client=SimpleNamespace(passive=True,tick=Mock())
        app=SimpleNamespace(update_client=client,model=SimpleNamespace(state=State.HOME),
            engine=None,setup_stage=None,settings_open=False,setup_busy=False,
            settings_draft=SimpleNamespace(busy=False),keys_down=set(),last_button=0,
            language='fr',closed=False,usb_power=SimpleNamespace(enabled=True,powered=None,state='starting',deferred=True))
        tick_terminal(app,200)
        self.assertTrue(client.tick.call_args.args[0])
        self.assertTrue(client.tick.call_args.args[3])
        app.usb_power.deferred = False
        app.usb_power.state = 'on'
        app.usb_power.powered = True
        tick_terminal(app, 200)
        self.assertFalse(client.tick.call_args.args[3])
        client.passive=False
        app.usb_power.state = 'starting'
        tick_terminal(app,200)
        self.assertFalse(client.tick.call_args.args[0])
        self.assertFalse(client.tick.call_args.args[3])
    def test_tv_shutdown_during_update_does_not_start_restoration(self):
        from zmala_terminal.linux.tv_control import TVControl
        television = TVControl(device='/fixture/not-a-cec-device')
        television.cancel = Mock()
        television.hold_for_update()
        television.close()
        television.cancel.assert_not_called()

    def test_deferred_usb_does_not_start_or_restore_power_until_activity(self):
        from zmala_terminal.linux.usb_power import UsbPower
        with patch('zmala_terminal.linux.usb_power.sys.platform', 'linux'), patch.dict(os.environ, {'ZMALA_USB_POWER': '1'}), patch('zmala_terminal.linux.usb_power.threading.Thread') as thread:
            power = UsbPower(Path('.'), defer=True)
            thread.assert_not_called()
            power.command = Mock()
            power.hold_for_update()
            power.stopped = True
            power.run()
            power.command.assert_not_called()
            power.stopped = False
            power.require()
            thread.assert_called_once()
            self.assertFalse(power.preserve_shutdown)
            power.close()

    def test_admitted_calls_and_buttons_do_not_touch_media_or_model(self):
        app=SimpleNamespace(update_client=SimpleNamespace(locked=True),engine=Mock(),model=Mock(),usb_power=Mock())
        CallControl.call_event(app,'incoming',1,'caller','domain')
        app.engine.call_decline.assert_called_once_with('incoming',6)
        app.model.incoming.assert_not_called();app.usb_power.require.assert_not_called()
        self.assertEqual(InputControl.keypress(app,'green'),'break')
        CallControl.action(app,'dial');app.engine.dial.assert_not_called()
        passive=SimpleNamespace(defer_media=True)
        Engine.apply_settings(passive,{})
        self.assertIsNone(Engine.apply_speaker_volume(passive))

    @unittest.skipUnless(os.name=='posix','POSIX no-follow IPC')
    def test_lease_freshness_and_passive_release(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);request=root/'request';status=root/'status';now=[100]
            value={'nonce':'a'*32,'heartbeat':100,'phase':'request','preserve_sleep':True}
            request.write_text(json.dumps(value));client=UpdateClient(request,status,lambda:now[0],os.getuid())
            client.tick(False,'fr',True,True);self.assertFalse(client.locked)
            fence=Mock(side_effect=lambda: self.assertFalse(status.exists() and json.loads(status.read_text())['maintenance']))
            now[0]+=1;client.tick(True,'fr',True,True,on_fence=fence)
            fence.assert_called_once()
            reply=json.loads(status.read_text());self.assertTrue(reply['maintenance']);self.assertEqual(reply['language'],'fr')
            self.assertTrue(client.passive)
            now[0]=115;client.tick(False,'fr',True,True);self.assertFalse(client.locked)
            value.update(phase='checking',heartbeat=115);request.write_text(json.dumps(value));client.refresh()
            self.assertTrue(client.locked)
            now[0]=130;client.tick(False,'fr',True,True);self.assertTrue(client.locked)
            value.update(phase='idle',heartbeat=130);request.write_text(json.dumps(value));client.refresh()
            self.assertFalse(client.locked);client.activity();self.assertFalse(client.passive)
            client.refresh();self.assertFalse(client.passive)
            value.update(nonce='b'*32);request.write_text(json.dumps(value));client.refresh()
            self.assertFalse(client.passive)
            request.unlink();request.symlink_to(status)
            self.assertIsNone(client.refresh())
            request.unlink();request.write_text('{');self.assertIsNone(client.refresh())
