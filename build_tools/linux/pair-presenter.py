"""Presenter+ pairing and reconnect recovery without a desktop.

Allow the saved Presenter to reconnect before looking for a replacement. Pair
one matching advertised device at a time; the agent rejects all others.
Runs outside Tk/media, with bounded D-Bus calls and retry backoff.
"""
import json
import logging
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid

NAME = 'Microsoft Presenter+'
HID = '00001812-0000-1000-8000-00805f9b34fb'
STATUS = Path('/run/zmalacall-pairing/status.json')
AGENT = '/org/zmalacall/PresenterAgent'
BOND = Path('/var/lib/zmalacall-pairing/bond.json')
RECONNECT_SECONDS = 60
RESET_REQUEST = Path('/var/lib/zmalacall/remote-reset.json')
RESET_STATE = Path('/var/lib/zmalacall-pairing/reset.json')


def reset_request():
    """Read only the configured application user's bounded, fixed-name command."""
    if not os.environ.get('ZMALA_USER'):
        return None
    import pwd
    try:
        uid = pwd.getpwnam(os.environ['ZMALA_USER']).pw_uid
        if uid == 0:
            return None
        directory = os.open(RESET_REQUEST.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory)
            if info.st_uid != uid or info.st_mode & 0o022:
                return None
            fd = os.open(RESET_REQUEST.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        finally:
            os.close(directory)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_mode & 0o077 or info.st_size > 256:
                return None
            value = json.loads(stream.read(257))
        identity = value.get('request') if isinstance(value, dict) and value.get('schema') == 1 else None
        return identity if isinstance(identity, str) and re.fullmatch('[0-9a-f]{32}', identity) else None
    except (OSError, ValueError, KeyError):
        return None


def reset_state():
    try:
        value = json.loads(RESET_STATE.read_text())
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}


def save_reset(value):
    temporary = RESET_STATE.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, RESET_STATE)
    fd = os.open(RESET_STATE.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def saved_bond():
    try:
        saved = json.loads(BOND.read_text())
        if isinstance(saved, dict):
            return saved
    except (OSError, ValueError):
        pass
    return {}


def bond_token(device, renew=False):
    """An opaque test identity, never a Bluetooth key; stable across reboots."""
    saved = saved_bond()
    if not renew and saved.get('device') == device and isinstance(saved.get('token'), str):
        return saved['token']
    token = uuid.uuid4().hex
    temp = BOND.with_suffix('.tmp')
    temp.write_text(json.dumps({'device': device, 'token': token}))
    os.replace(temp, BOND)
    return token
XML = '''<node><interface name="org.bluez.Agent1">
<method name="Release"/><method name="Cancel"/>
<method name="RequestAuthorization"><arg type="o" direction="in"/></method>
<method name="RequestConfirmation"><arg type="o" direction="in"/><arg type="u" direction="in"/></method>
<method name="AuthorizeService"><arg type="o" direction="in"/><arg type="s" direction="in"/></method>
<method name="RequestPinCode"><arg type="o" direction="in"/><arg type="s" direction="out"/></method>
<method name="RequestPasskey"><arg type="o" direction="in"/><arg type="u" direction="out"/></method>
</interface></node>'''


def is_presenter(properties):
    return properties.get('Name') == NAME and HID in properties.get('UUIDs', [])


# @llr LLR-TERM-SETUP-023
def candidate(devices):
    """Do not choose between multiple nearby remotes or pair stale cache entries."""
    matches = [path for path, props in devices.items() if is_presenter(props)
               and not props.get('Paired') and not props.get('Blocked') and 'RSSI' in props]
    return matches[0] if len(matches) == 1 else None


class Pairing:
    def __init__(self):
        from gi.repository import Gio, GLib
        self.Gio, self.GLib = Gio, GLib
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.target = None
        self.replacing = None
        self.reconnect_until = None
        self.startup_reconnect = True
        self.retry_at = 0
        self.state = None
        self.discovery = None
        self.loop = GLib.MainLoop()
        self.failed = False
        info = Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0]
        self.bus.register_object(AGENT, info, self.authorize, None, None)
        self.call('/org/bluez', 'org.bluez.AgentManager1', 'RegisterAgent', '(os)', (AGENT, 'NoInputNoOutput'))

    def call(self, path, interface, method, signature=None, values=()):
        args = self.GLib.Variant(signature, values) if signature else None
        return self.bus.call_sync('org.bluez', path, interface, method, args, None,
                                  self.Gio.DBusCallFlags.NONE, 3000, None).unpack()

    def set_property(self, path, interface, name, value):
        self.call(path, 'org.freedesktop.DBus.Properties', 'Set', '(ssv)',
                  (interface, name, self.GLib.Variant('b', value)))

    def authorize(self, connection, sender, path, interface, method, parameters, invocation):
        values = parameters.unpack()
        allowed = method in ('Release', 'Cancel') or (
            method in ('RequestAuthorization', 'RequestConfirmation', 'AuthorizeService')
            and values and values[0] == self.target)
        if allowed:
            invocation.return_value(None)
        else:
            invocation.return_dbus_error('org.bluez.Error.Rejected', 'Only the selected Presenter can pair')

    def publish(self, state, bond=None, reconnect_seconds=None):
        payload = {'state': state}
        completed = reset_state()
        if completed.get('done'):
            payload['reset_request'] = completed['request']
        if bond:
            payload['bond'] = bond
        if reconnect_seconds is not None:
            payload['reconnect_seconds'] = reconnect_seconds
        if payload != self.state:
            temp = STATUS.with_suffix('.tmp')
            temp.write_text(json.dumps(payload) + '\n')
            temp.chmod(0o644)
            os.replace(temp, STATUS)
            if self.state is None or self.state['state'] != state:
                logging.info('Remote setup: %s', state)
            self.state = payload

    def paired(self, connection, result, unused):
        target = self.target
        try:
            connection.call_finish(result)
            self.set_property(target, 'org.bluez.Device1', 'Trusted', True)
            token = bond_token(target, renew=True)
            if self.replacing:
                try:
                    self.call(self.discovery, 'org.bluez.Adapter1', 'RemoveDevice', '(o)', (self.replacing,))
                except self.GLib.Error as error:
                    logging.warning('Could not remove previous Presenter pairing: %s', error.message)
            # Pair normally connects HID too. Do not block agent dispatch while
            # waiting for Connect; the normal BlueZ reconnection policy applies.
            self.bus.call('org.bluez', target, 'org.bluez.Device1', 'Connect', None, None,
                          self.Gio.DBusCallFlags.NONE, 10000, None, self.connected, None)
            self.reconnect_until = None
            self.startup_reconnect = False
            self.publish('paired', token)
        except self.GLib.Error as error:
            logging.warning('Pairing did not finish: %s', error.message)
            self.retry_at = time.monotonic() + 10
            if not self.replacing:
                self.publish('unpaired')
        finally:
            self.target = None
            self.replacing = None

    def connected(self, connection, result, unused):
        try:
            connection.call_finish(result)
        except self.GLib.Error:
            logging.info('Waiting for the paired remote to reconnect')

    # @llr LLR-TERM-SETUP-033
    def reset_remote(self, devices):
        identity = reset_request()
        saved = reset_state()
        if not identity or (saved.get('request') == identity and saved.get('done')):
            return False
        if self.target:
            return True  # Let the bounded pairing callback finish before removing its bond.
        if saved.get('request') != identity:
            paired = [path for path, props in devices.items() if is_presenter(props) and props.get('Paired')]
            preferred = saved_bond().get('device')
            target = preferred if preferred in paired else next(iter(paired), None)
            saved = {'request': identity, 'device': target, 'done': False}
            save_reset(saved)  # Resume this exact removal after interruption, not another remote.
        target = saved.get('device')
        if target in devices:
            adapter = devices[target].get('Adapter')
            if not adapter:
                raise ValueError('Remote adapter unavailable during reset')
            self.call(adapter, 'org.bluez.Adapter1', 'RemoveDevice', '(o)', (target,))
        BOND.unlink(missing_ok=True)
        saved['done'] = True
        save_reset(saved)
        self.reconnect_until = None
        self.startup_reconnect = False
        self.publish('unpaired')
        return True

    def tick(self):
        try:
            objects, = self.call('/', 'org.freedesktop.DBus.ObjectManager', 'GetManagedObjects')
            adapters = {path: interfaces['org.bluez.Adapter1'] for path, interfaces in objects.items()
                        if 'org.bluez.Adapter1' in interfaces}
            devices = {path: interfaces['org.bluez.Device1'] for path, interfaces in objects.items()
                       if 'org.bluez.Device1' in interfaces}
            if not adapters:
                self.publish('bluetooth_unavailable')
                return True
            try:
                if self.reset_remote(devices):
                    return True
            except (OSError, ValueError, self.GLib.Error):
                logging.exception('Remote reset pending; retrying before pairing')
                self.publish('bluetooth_unavailable')
                return True
            adapter, props = next(iter(adapters.items()))
            if not props.get('Powered'):
                self.set_property(adapter, 'org.bluez.Adapter1', 'Powered', True)
            if self.target:
                return True
            saved = [path for path, props in devices.items() if is_presenter(props) and props.get('Paired')]
            previous = None
            now = time.monotonic()
            if saved:
                preferred = saved_bond().get('device')
                previous = preferred if preferred in saved else saved[0]
                remote = devices[previous]
                if not remote.get('Trusted') and not remote.get('Blocked'):
                    self.set_property(previous, 'org.bluez.Device1', 'Trusted', True)
                connected = remote.get('Connected')
                if connected:
                    self.reconnect_until = None
                    self.startup_reconnect = False
                if not self.startup_reconnect:
                    seconds = None
                else:
                    if self.reconnect_until is None:
                        self.reconnect_until = now + RECONNECT_SECONDS
                    seconds = max(0, math.ceil(self.reconnect_until - now))
                self.publish('paired', bond_token(previous), seconds)
                if seconds != 0:
                    if self.discovery:
                        self.call(self.discovery, 'org.bluez.Adapter1', 'StopDiscovery')
                        self.discovery = None
                    return True
            else:
                self.reconnect_until = None
                self.publish('unpaired')
            if not self.discovery:
                self.call(adapter, 'org.bluez.Adapter1', 'SetDiscoveryFilter', '(a{sv})',
                          ({'Transport': self.GLib.Variant('s', 'le'),
                            'UUIDs': self.GLib.Variant('as', [HID])},))
                self.call(adapter, 'org.bluez.Adapter1', 'StartDiscovery')
                self.discovery = adapter
                return True
            target = candidate(devices)
            if target and now >= self.retry_at:
                self.target = target
                self.replacing = previous
                if not previous:
                    self.publish('pairing')
                self.bus.call('org.bluez', target, 'org.bluez.Device1', 'Pair', None, None,
                              self.Gio.DBusCallFlags.NONE, 45000, None, self.paired, None)
        except self.GLib.Error as error:
            logging.warning('Bluetooth setup unavailable: %s', error.message)
            self.publish('bluetooth_unavailable')
            # A restarted BlueZ loses this connection's registered agent. Let
            # systemd recreate it instead of silently scanning without an agent.
            self.failed = True
            self.loop.quit()
            return False
        return True


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    pairing = Pairing()
    if not pairing.tick():
        raise SystemExit(1)
    pairing.GLib.timeout_add_seconds(1, pairing.tick)
    pairing.loop.run()
    if pairing.failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
