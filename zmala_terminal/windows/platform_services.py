"""Desktop substitutes for Pi-only power and television services.

Windows call ringing stays in the native call engine. These objects deliberately
perform no USB, CEC or I2C work. Ringtone previews use the Windows sound device
with independent gain and a bounded, cancellable playback timer.
"""
from pathlib import Path
import threading
import wave


def play_sound(file):
    import winsound
    winsound.PlaySound(str(file) if file else None,
                      winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT if file else 0)


class DesktopFan:
    def update(self, active):
        pass

    def close(self):
        pass


class DesktopTelevision:
    supports_setup = True
    simulated = True
    simulation_scene = None
    power_enabled = True
    source_enabled = True

    def select_driver(self, name):
        from zmala_terminal.linux.tv_plugins import DRIVERS
        if name not in DRIVERS:
            raise ValueError('Unknown TV driver')
        self._driver_name = name

    def handle_button(self, on_visible, preserve_restore=False):
        return False  # The desktop already shows the UI; do not consume the press.

    def wake(self, restore=True, initial=None, ringing=None):
        pass

    def cancel(self, defer=False):
        pass

    def pause_for_setup(self):
        pass

    def browsing_session(self):
        return None

    def restore_browsing(self, session):
        pass

    def ready(self, now):
        return True

    def close(self):
        pass


# @llr LLR-TERM-TV-019
class SimulatedTVTransport:
    """Exercise the real wizard without sending CEC or network commands."""
    def __init__(self, television):
        self.tv = television

    def probe(self, cancel):
        return {'address': '2.0.0.0', 'display': 'windows-simulated-tv'}

    def resume_network(self, enabled):
        pass

    def sequence(self, cancel, scenes):
        try:
            for scene in scenes:
                self.tv.simulation_scene = scene
                if cancel.wait(1.5):
                    return False
            return True
        finally:
            self.tv.simulation_scene = None

    def power(self, cancel):
        return self.sequence(cancel, ('standby', 'terminal'))

    def source(self, cancel):
        return self.sequence(cancel, ('broadcast', 'terminal', 'broadcast', 'terminal'))

    def discover(self, cancel):
        return [{'name': 'Simulated Samsung TV', 'host': '192.0.2.10'}]

    def pair(self, cancel, host):
        return True

    def confirm_source(self):
        pass


class DesktopPower:
    enabled = False
    ready = True
    power_state = None
    state = 'unsupported'
    playback_active = False

    def __init__(self, root):
        self.ringing = False
        self.stopped = False
        self.ringtone_file = Path(root) / 'common/assets/gentle-chime.wav'
        self.ringtone_volume = 50
        self.ringtone_preview_status = ''
        from zmala_terminal.linux.sound_levels import ToneLevels
        self.tone_levels = ToneLevels()
        self.preview_lock = threading.RLock()
        self.preview_timer = None
        self.preview_generation = 0

    def require(self, urgent=False):
        return True

    def set_mode(self, mode):
        pass

    def refresh(self, engine):
        pass

    def update(self, active, battery, ringing=False):
        self.ringing = ringing
        if ringing:
            self.stop_preview()

    def set_ringtone(self, file, percent=50):
        self.ringtone_file = Path(file)
        self.ringtone_volume = percent

    # @llr LLR-TERM-AUDIO-009
    def preview_tone(self, file):
        with self.preview_lock:
            self.stop_preview()
            if self.ringing or self.stopped:
                return
            if not self.ringtone_volume:
                self.ringtone_preview_status = 'muted'
                return
            try:
                prepared = self.tone_levels.prepare(file, self.ringtone_volume)
                with wave.open(str(prepared), 'rb') as audio:
                    duration = min(10, audio.getnframes()/audio.getframerate())
                play_sound(prepared)
                self.ringtone_preview_status = 'playing'
                generation = self.preview_generation
                self.preview_timer = threading.Timer(duration, self.finish_preview, (generation,))
                self.preview_timer.daemon = True
                self.preview_timer.start()
            except (OSError, ValueError, RuntimeError, wave.Error):
                self.stop_preview()
                self.ringtone_preview_status = 'error'

    def finish_preview(self, generation):
        with self.preview_lock:
            if generation == self.preview_generation:
                self.stop_preview()

    def stop_preview(self):
        with self.preview_lock:
            self.preview_generation += 1
            if self.preview_timer:
                self.preview_timer.cancel()
                self.preview_timer = None
            if self.ringtone_preview_status == 'playing':
                play_sound(None)
            self.ringtone_preview_status = ''

    def stop_ringing(self):
        self.ringing = False
        self.stop_preview()

    def close(self):
        self.stopped = True
        self.stop_ringing()
        self.tone_levels.close()


class DesktopRemote:
    supported = False
    connected = None
    battery = None
    charger_connected = None
    status = None

    def close(self):
        pass


class DesktopSounds:
    def set_enabled(self, enabled):
        pass

    def play(self, percent, button='left'):
        pass

    def cancel(self):
        pass

    def close(self):
        pass


class DesktopPairing:
    path = None
    state = None
    bond = None

    def read(self):
        return None


class DesktopCameraStatus:
    enabled = False

    def read(self):
        return None
