"""Remote-only update choice. The privileged updater owns all installation I/O."""
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

OFFER = Path('/run/zmalacall-updater/offer.json')
COMMAND = Path('/run/zmalacall/update-command.json')


def read_record(path, uid):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != uid or info.st_mode & 0o022 or info.st_size > 4096:
            raise ValueError('Untrusted update record')
        return json.loads(stream.read(4097))


# @llr LLR-TERM-MAINT-028
class UpdateMenu:
    def __init__(self, offer=OFFER, command=COMMAND, clock=time.monotonic):
        self.offer, self.command, self.clock = offer, command, clock
        self.state = 'unavailable'
        self.release = ''
        self.version = ''
        self.identity = ''
        self.deadline = 0
        self.next_poll = 0
        self.blockers = []
        if os.name == 'posix':
            try:
                ready = read_record(self.offer, 0)
                if isinstance(ready, dict) and ready.get('schema') == 1:
                    self.send('check')
                    self.state = 'checking'
            except (OSError, ValueError):
                pass

    def send(self, action):
        self.identity = uuid.uuid4().hex
        now = self.clock()
        payload = {'schema': 1, 'request': self.identity, 'action': action, 'issued': now}
        if action == 'apply':
            payload['release'] = self.release
        temporary = self.command.with_name('.update-command-'+self.identity)
        try:
            with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
                json.dump(payload, stream)
            os.replace(temporary, self.command)
        finally:
            temporary.unlink(missing_ok=True)
        self.deadline = now+40

    def poll(self):
        if self.state not in ('checking', 'submitting', 'queued', 'waiting') or self.clock() < self.next_poll:
            return False
        self.next_poll = self.clock()+.25
        timed_out = False
        if self.clock() >= self.deadline:
            if self.state in ('queued', 'waiting'):
                timed_out = self.state != 'waiting'
                self.state = 'waiting'  # Older owners may still be retrying; do not claim cancellation.
            else:
                self.state = 'error'
                return True
        try:
            value = read_record(self.offer, 0)
            if not isinstance(value, dict) or value.get('schema') != 1 or value.get('request') != self.identity:
                return timed_out
            state = value.get('state')
            if state == 'queued' and self.state == 'waiting':
                return timed_out
            if state == 'available':
                version, release = value.get('version'), value.get('release')
                if (not isinstance(version, str) or not re.fullmatch(r'[0-9]{1,8}\.[0-9]{1,8}\.[0-9]{1,8}', version)
                        or not isinstance(release, str) or not re.fullmatch('[0-9a-f]{64}', release)):
                    return timed_out
                self.version, self.release = version, release
            elif state not in ('current', 'error', 'unavailable', 'queued'):
                return timed_out
            changed = self.state != state
            if state == 'queued' and self.state == 'submitting':
                self.deadline = self.clock()+30
            reasons = value.get('blockers', [])
            self.blockers = [item for item in (reasons if isinstance(reasons, list) else [])
                             if item in ('call', 'setup', 'settings', 'input', 'worker', 'usb', 'tv', 'idle', 'terminal')]
            self.state = state
            return changed
        except (OSError, ValueError):
            return timed_out

    def apply(self):
        if self.state == 'error':
            try:
                self.send('check')  # Obtain a fresh verified offer before retrying Apply.
            except OSError:
                return False
            self.state = 'checking'
            return True
        if self.state != 'available':
            return False
        try:
            self.send('apply')
        except OSError:
            self.state = 'error'
            return False
        self.state = 'submitting'
        return True
