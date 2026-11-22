"""State for the local server page. HTTP runs off the Tk thread."""
import json
import queue
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from zmala_terminal.common.json_storage import write_json


_messages = json.loads((Path(__file__).parent/'shared/server-page-messages.json').read_text(encoding='utf-8'))
LABELS = {language: dict(zip(_messages['en'], labels, strict=True)) for language, labels in _messages.items()}


def server_label(language, label):
    return LABELS.get(language, LABELS['en']).get(label, label)


def service_running():
    try:
        return subprocess.run(['systemctl', 'is-active', '--quiet', 'zmalacall-server'],
                              timeout=3, check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class ServerPage:
    def __init__(self, directory, first=False):
        self.first = first
        self.revision = 0
        self.index = 0
        self.busy = False
        self.start_requested = False
        self.next_read = 0
        self.responses = queue.SimpleQueue()
        self.details = {}
        self.stage = 'starting' if first else 'loading'
        self.confirm_call = False
        self.record = directory / 'server-access-check.json'
        try:
            self.history = json.loads(self.record.read_text(encoding='utf-8'))
            if not isinstance(self.history, dict):
                self.history = {}
        except (OSError, ValueError):
            self.history = {}

    @property
    def actions(self):
        if self.confirm_call:
            return ('Confirm two-way audio and video',)
        if self.stage in ('stopped', 'disconnected'):
            return ('Retry connection' if self.stage == 'disconnected' else 'Try again',)
        if self.stage != 'connected':
            return ()
        return tuple(action for action in (
            'Test with a phone' if self.details.get('origin') else '',
            'Confirm a remote call' if self.details.get('origin') else '',
            'Continue to contacts' if self.first else '') if action)

    def select(self, step):
        if self.actions:
            self.index = (self.index + step) % len(self.actions)
            self.revision += 1

    def read(self, configuration, *, start=False):
        self.start_requested |= start
        if self.busy or not configuration:
            return
        start, self.start_requested = self.start_requested, False
        self.busy = True
        def worker():
            try:
                response = configuration.request('/api/device/server-configuration', {} if start else None)
                details = json.loads(response)
                if not isinstance(details, dict) or 'state' not in details:
                    raise ValueError('Invalid server status')
                self.responses.put(('connected', details))
            except (OSError, ValueError, RuntimeError):
                self.responses.put(('disconnected' if service_running() else 'stopped', {}))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self, configuration):
        try:
            stage, details = self.responses.get_nowait()
        except queue.Empty:
            if time.monotonic() >= self.next_read and self.stage not in ('starting', 'stopped', 'disconnected'):
                self.read(configuration)
            return False
        self.busy = False
        self.next_read = 0 if self.start_requested else time.monotonic() + (2 if details.get('state') == 'waiting' else 8)
        if (stage, details) == (self.stage, self.details):
            return False
        self.stage, self.details = stage, details
        self.index = min(self.index, max(0,len(self.actions)-1))
        self.revision += 1
        if details.get('checked'):
            self.remember('reached', details['checked'])
        return True

    def remember(self, field, milliseconds):
        origin = self.details.get('origin')
        if origin:
            if self.history.get('origin') != origin:
                self.history = {'origin': origin}
            self.history[field] = milliseconds
            write_json(self.record, self.history)

    def when(self, field):
        if self.history.get('origin') != self.details.get('origin'):
            return ''
        try:
            return datetime.fromtimestamp(self.history[field]/1000).strftime('%d %b %Y, %H:%M')
        except (KeyError, ValueError, TypeError, OverflowError, OSError):
            return ''
