"""Prepare uploaded GIF portraits early and play only the settled selected card.

Static portrait rendering remains the fallback during navigation and calls. All Tk objects
are created on the UI thread, in small batches, and retained under a 64 MiB cap.
"""

from collections import OrderedDict
import io
import queue
import threading
import time
from pathlib import Path
import tkinter as tk
import logging
from PIL import Image

LIMIT = 64 * 1024 * 1024
PRELOAD_LIMIT = 48 * 1024 * 1024


# @llr LLR-TERM-UI-026
def load_frames(path, size):
    """Decode in a worker, composite GIF disposal, bound work before Tk allocation."""
    from zmala_terminal.common.photo_cache import valid_photo
    from zmala_terminal.common.image_bounds import MAX_GIF_BYTES

    with path.open("rb") as stream:
        data = stream.read(MAX_GIF_BYTES + 1)
    if not valid_photo(data, path.name):
        raise ValueError("Invalid animated portrait")
    if not 40 <= size <= 460:
        raise ValueError("Invalid portrait display size")
    pngs, durations = [], []
    with Image.open(io.BytesIO(data)) as source:
        for index in range(source.n_frames):
            source.seek(index)
            frame = source.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            frame.save(out, format="PNG")
            pngs.append(out.getvalue())
            durations.append(source.info.get("duration", 100) or 100)
    return pngs, durations


# @llr LLR-TERM-UI-026
class PortraitAnimation:
    def __init__(self, app, directory):
        self.app = app
        self.directory = Path(directory)
        self.completed = 0
        self.error_count = 0
        self.cache = OrderedDict()
        self.preloaded = OrderedDict()
        self.preload_targets = ()
        self.preload_attempted = set()
        self.preload_retry_at = 0
        self.results = queue.Queue()
        self.loading = None
        self.build = None
        self.key = None
        self.armed = True
        self.playing = False
        self.started = 0
        self.frame = -1
        self.visible_photo = None
        self.painted_item = None
        self.failures = set()
        self.app.root.after(20, self.tick)

    def request(self, key):
        if self.loading or self.build or key in self.failures:
            return
        photo, size = key
        folder = (self.directory / photo.lstrip("/")).resolve()
        if not folder.is_relative_to(self.directory.resolve()):
            raise ValueError("Invalid portrait path")
        if not folder.is_file():
            return  # The photo worker may still be downloading.
        self.loading = key

        def worker():
            try:
                self.results.put((key, load_frames(folder, size), None))
            except Exception as e:
                self.results.put((key, None, type(e).__name__))

        threading.Thread(target=worker, daemon=True).start()

    def prepare(self):
        try:
            key, result, error = self.results.get_nowait()
        except queue.Empty:
            return
        self.loading = None
        if key != self.key and key not in self.preload_targets:
            return  # The contact or its display size changed while decoding.
        if error:
            self.failures.add(key)
            logging.warning("Animated portrait unavailable: %s", error)
            return
        if key == self.key:
            self.start_build(key, *result)
            return
        pngs, durations = result
        needed = sum(map(len, pngs))
        if needed <= PRELOAD_LIMIT:
            while self.preloaded and sum(value[2] for value in self.preloaded.values()) + needed > PRELOAD_LIMIT:
                self.preloaded.popitem(last=False)
            self.preloaded[key] = (pngs, durations, needed)
        self.preload_attempted.add(key)

    def start_build(self, key, pngs, durations):
        needed = len(pngs) * key[1] * key[1] * 4
        while self.cache and sum(v[2] for v in self.cache.values()) + needed > LIMIT:
            self.cache.popitem(last=False)
        self.build = (key, pngs, durations, [], needed)
        self.preload_attempted.add(key)

    def preload(self, now):
        if self.loading or self.build or now < self.preload_retry_at:
            return
        for key in self.preload_targets:
            if key not in self.preload_attempted and key not in self.cache:
                self.request(key)
                if self.loading:
                    return
        # Some files may still be downloading. Avoid probing every Tk tick.
        self.preload_retry_at = now + 1

    def build_images(self):
        if not self.build:
            return
        key, pngs, durations, photos, needed = self.build
        if key != self.key:
            self.build = None
            return
        for _ in range(min(4, len(pngs) - len(photos))):
            photos.append(
                tk.PhotoImage(
                    master=self.app.root, data=pngs[len(photos)], format="png"
                )
            )
        if len(photos) == len(pngs):
            self.cache[key] = (photos, durations, needed)
            self.build = None

    def paint(self, photo):
        items = self.app.avatar.find_withtag("portrait-preview-target")
        item = items[-1] if items else None
        if item and (photo is not self.visible_photo or item != self.painted_item):
            self.app.avatar.itemconfigure(item, image=photo)
            self.painted_item = item
        self.visible_photo = photo

    def close(self):
        self.playing = False
        self.key = None
        self.visible_photo = None
        self.build = None
        self.cache.clear()
        self.preloaded.clear()

    def tick(self):
        app = self.app
        if app.closed:
            return
        try:
            from zmala_terminal.common.model import State

            target = getattr(app, "portrait_animation_target", None)
            selected = app.model.selected
            eligible = (
                app.model.state == State.HOME
                and not app.setup_stage
                and not app.settings_open
                and not app.carousel_motion
                and selected
                and target
                and selected["id"] == target[0]
            )
            photo = selected.get("photo", "") if selected else ""
            key = None
            if eligible and photo.endswith(".gif") and app.avatar.find_withtag("portrait-preview-target"):
                key = (photo, target[1])
            if key != self.key:
                self.key = key
                self.armed = True
                self.playing = False
                self.frame = -1
                self.visible_photo = None
                self.painted_item = None
            if app.model.state != State.HOME or app.setup_stage:
                self.cache.clear()
                self.preloaded.clear()
                self.preload_targets = ()
                self.preload_attempted.clear()
                self.build = None
            elif eligible:
                targets = tuple(dict.fromkeys(
                    (person["photo"], target[1]) for person in (selected, *app.model.contacts)
                    if person.get("photo", "").endswith(".gif")
                ))
                if targets != self.preload_targets:
                    self.preload_targets = targets
                    self.preload_attempted.intersection_update(targets)
                    for obsolete in self.preloaded.keys() - set(targets):
                        del self.preloaded[obsolete]
                    self.preload_retry_at = 0
            self.prepare()
            self.build_images()
            if key:
                if key not in self.cache:
                    if key in self.preloaded:
                        pngs, durations, _ = self.preloaded.pop(key)
                        self.start_build(key, pngs, durations)
                    else:
                        self.request(key)
                else:
                    self.cache.move_to_end(key)
                    photos, durations, _ = self.cache[key]
                    now = time.monotonic()
                    if self.armed:
                        self.armed = False
                        self.playing = True
                        self.started = now
                    if self.playing:
                        elapsed = (now - self.started) * 1000
                        boundary = 0
                        index = 0
                        for index, duration in enumerate(durations):
                            boundary += duration
                            if elapsed < boundary:
                                break
                        else:
                            self.playing = False
                            index = len(photos) - 1
                            self.completed += 1
                        self.paint(photos[index])
                        if self.frame != index:
                            self.frame = index
                    elif self.visible_photo:
                        # A presence refresh may redraw the card; keep the final still frame.
                        self.paint(self.visible_photo)
            if eligible:
                self.preload(time.monotonic())
        except Exception as e:
            self.error_count += 1
            logging.warning("Animated portrait playback stopped: %s", type(e).__name__)
            self.playing = False
        app.root.after(10 if self.playing or self.build else 30, self.tick)
