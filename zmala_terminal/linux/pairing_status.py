"""Read the installer-enabled pairing service without blocking the UI."""
import json
import os
from pathlib import Path
import time
import uuid

from zmala_terminal.common.paths import ROOT

RESET_REQUEST = ROOT / 'data' / 'remote-reset.json'


class PairingStatus:
    def __init__(self):
        self.path = os.environ.get('ZMALA_PAIRING_STATUS')
        self.next_read = 0
        self.state = None
        self.bond = None
        self.reconnect_seconds = None

    # @llr LLR-TERM-SETUP-033
    def reset(self):
        if not self.path:
            return
        temporary = RESET_REQUEST.with_suffix('.tmp')
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
            json.dump({'schema': 1, 'request': uuid.uuid4().hex}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, RESET_REQUEST)
        fd = os.open(RESET_REQUEST.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.next_read = 0

    def read(self):
        if not self.path:
            return None  # Desktop/test launchers do not require a Presenter.
        now = time.monotonic()
        if now >= self.next_read:
            self.next_read = now + .5
            self.reconnect_seconds = None
            try:
                payload = json.loads(Path(self.path).read_text())
                if RESET_REQUEST.exists():
                    requested = json.loads(RESET_REQUEST.read_text())['request']
                    if payload.get('reset_request') != requested:
                        self.state, self.bond = 'pairing', None
                        return self.state
                    RESET_REQUEST.unlink()
                self.state = payload['state']
                self.bond = payload.get('bond') if isinstance(payload.get('bond'), str) else None
                if self.state not in ('paired', 'pairing', 'unpaired', 'bluetooth_unavailable'):
                    self.state = 'bluetooth_unavailable'
                seconds = payload.get('reconnect_seconds')
                if self.state == 'paired' and type(seconds) is int and 0 <= seconds <= 60:
                    self.reconnect_seconds = seconds
            except (OSError, ValueError, KeyError, TypeError):
                self.state = 'bluetooth_unavailable'
                self.bond = None
        return self.state
