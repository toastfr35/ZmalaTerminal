"""Interactive acceptance fixture using the real Windows/Tk settings controllers.

Run through run_display.py to isolate all profile files. Settings acknowledgements
are in memory; no server, camera, microphone, network or TV commands are used.
"""
import queue
import time

from zmala_terminal.common.main import Terminal
from zmala_terminal.common.localization import font_family
from tests.terminal.LLT.test_terminal import config


class MemoryConfiguration:
    def __init__(self, value):
        self.value = value

    def update_settings(self, changes, expected):
        self.value = dict(self.value, **changes,
                          configuration_version=self.value['configuration_version']+1)
        return self.value


class Preview(Terminal):
    def restore_enrollment(self, *args):
        self.setup_stage = None

    def start_services(self):
        self.configuration = MemoryConfiguration(config() | {
            'device_id': 'WINDOWS-ACCEPTANCE', 'language': 'en', 'ringtone_volume': 50,
            'auto_answer': False, 'auto_answer_seconds': 30})
        self.apply_config(self.configuration.value)
        self.settings_open = True
        self.render()
        self.root.after(30, self.preview_tick)

    def apply_config(self, value):
        self.model.configure(value)
        self.language = value.get('language', 'en')
        self.font_family = font_family(self.language, self.available_fonts)

    def action(self, action):
        pass

    def preview_tick(self):
        self.tick_settings_access(time.monotonic())
        try:
            while True:
                kind, args = self.messages.get_nowait()
                if kind == 'local-settings':
                    self.local_settings_result(*args)
        except queue.Empty:
            pass
        self.root.after(30, self.preview_tick)


app = Preview(profile='settings-acceptance')
app.root.title('Zmala settings acceptance · Left/Right · Enter = green · Escape = red')
app.root.geometry('1280x720')
app.run()
