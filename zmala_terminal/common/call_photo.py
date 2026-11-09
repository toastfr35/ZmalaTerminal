"""Receive a leased, authenticated call photo without touching media or Tk off-thread."""
import io
import json
import queue
import threading
import time
import urllib.parse
import tkinter as tk
from typing import NamedTuple
from PIL import Image, ImageTk
from zmala_terminal.common.model import State

MAX_PHOTO_BYTES = 2 * 1024 * 1024
MAX_PHOTO_SIDE = 1600
MAX_LEASE_MS = 12000
POLL_SECONDS = 1


class PhotoResult(NamedTuple):
    owner: tuple
    revision: int | None = None
    image: Image.Image | None = None
    deadline: float = 0
    failed: bool = False


# @llr LLR-TERM-VIDEO-020
def decode_photo(data):
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError('Photo too large')
    with Image.open(io.BytesIO(data)) as image:
        if image.format != 'JPEG' or max(image.size) > MAX_PHOTO_SIDE:
            raise ValueError('Invalid call photo')
        return image.convert('RGB')


# @llr LLR-TERM-VIDEO-020
def fetch_photo(owner, revision, previous_image, started):
    """Return one detached worker result; failures never renew the visible lease."""
    _, call_id, configuration = owner
    try:
        route = '/api/call/photo?call_id=' + urllib.parse.quote(call_id, safe='')
        status = json.loads(configuration.request(route))
        if not isinstance(status, dict):
            raise ValueError('Invalid call photo status')
        value = status.get('revision')
        remaining = status.get('remaining_ms', 0)
        if (type(value) is not int or value < 0
                or type(status.get('sharing')) is not bool or type(remaining) is not int):
            raise ValueError('Invalid call photo status fields')
        deadline = started + min(MAX_LEASE_MS, max(0, remaining)) / 1000
        if not status['sharing'] or time.monotonic() >= deadline:
            return PhotoResult(owner, value, deadline=deadline)
        if value == revision and previous_image is not None:
            return PhotoResult(owner, value, previous_image, deadline)

        data = configuration.request(route + '&image=1&revision=' + str(value))
        # A slow transfer consumes the lease. Avoid decoding pixels we cannot show.
        if time.monotonic() >= deadline:
            return PhotoResult(owner, value, deadline=deadline)
        return PhotoResult(owner, value, decode_photo(data), deadline)
    except Exception:
        # Keep network/decoder failures off the UI thread and retain the old expiry.
        return PhotoResult(owner, failed=True)


# @llr LLR-TERM-VIDEO-020
class CallPhoto:
    def __init__(self, root):
        self.layer = tk.Label(root, bg='black', borderwidth=0)
        self.layer.bind('<Configure>', lambda event: self.draw())
        self.owner = None
        self.revision = None
        self.image = None
        self.picture = None
        self.results = queue.Queue()
        self.busy = False
        self.next_poll = 0
        self.deadline = 0
        self.drawn = None

    def clear(self):
        self.image = self.picture = self.revision = self.drawn = None
        self.layer.configure(image='')
        self.layer.place_forget()

    def draw(self):
        if self.image is None:
            return
        size = (max(1, self.layer.winfo_width()), max(1, self.layer.winfo_height()))
        # Tk initially reports 1x1 before placement; contain can round a side to zero.
        if min(size) < 2:
            return
        key = (self.revision, size)
        if self.drawn == key:
            return
        scale = min(size[0] / self.image.width, size[1] / self.image.height)
        target = (max(1, round(self.image.width * scale)), max(1, round(self.image.height * scale)))
        self.picture = ImageTk.PhotoImage(self.image.resize(target, Image.Resampling.LANCZOS))
        self.layer.configure(image=self.picture)
        self.drawn = key

    def tick(self, app):
        # Native SDK reads remain on its owner/Tk thread.
        call_id = None
        if app.engine and app.model.state == State.IN_CALL and app.model.config.get('call_photo_sharing'):
            call_id = app.engine.call_id()
        owner = (app.engine, call_id, app.configuration) if isinstance(call_id, str) and call_id and app.configuration else None
        if owner != self.owner:
            self.owner = owner
            self.clear()
            self.next_poll = 0
        now = time.monotonic()
        while not self.results.empty():
            result = self.results.get_nowait()
            self.busy = False
            if result.owner != self.owner or result.failed:
                continue
            self.deadline = result.deadline
            if result.revision != self.revision or result.image is None:
                self.clear()
                if result.image is not None and result.deadline > now:
                    self.revision, self.image = result.revision, result.image
                    self.layer.place(x=0, y=0, relwidth=1, relheight=1)
                    self.layer.lift()
                    self.draw()
        if self.image is not None and now >= self.deadline:
            self.clear()
        if owner is None or self.busy or now < self.next_poll:
            return
        self.busy = True
        self.next_poll = now + POLL_SECONDS
        revision = self.revision
        previous_image = self.image

        def fetch():
            self.results.put(fetch_photo(owner, revision, previous_image, now))

        try:
            threading.Thread(target=fetch, daemon=True, name='zmala-call-photo').start()
        except RuntimeError:
            self.busy = False  # Permit a later poll if the worker could not start.
