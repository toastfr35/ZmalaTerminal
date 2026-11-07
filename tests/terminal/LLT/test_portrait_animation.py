# @test T-LLT-085
# @requirements LLR-TERM-UI-020, LLR-TERM-UI-026
# @environment portable
# @plan Drive the real animation controller with a fake Tk/canvas boundary and real GIF decoding. Assert single play, final-frame hold, reselect replay, call/navigation cancellation, bounded cache eviction, missing-file recovery and rejection of invalid bytes/dimensions. Start on a contact without a photo and verify other GIFs preload without Tk allocation. Select a warmed contact and check playback reuses the decoded frames.
# @pass Every state, frame, canvas target, byte-budget and cancellation assertion passes; this is not a physical display run.
"""Portable scheduler tests; no SIP, camera, remote or real Tk display."""
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tests.support.terminal.portrait_fixture import make_gif
from zmala_terminal.common import portrait_animation as animation
from zmala_terminal.common.model import State

class Root:
    def after(self, *args): pass
class Canvas:
    def __init__(self): self.photo=None; self.paints=0
    def find_withtag(self, tag): return [7]
    def itemconfigure(self, item, image):
        assert item == 7
        self.photo=image; self.paints+=1

class AnimationTests(unittest.TestCase):
    def pump(self, player, condition):
        until=time.monotonic()+5
        while not condition():
            player.tick()
            self.assertLess(time.monotonic(),until,'Playback timed out')
            time.sleep(.005)
    def test_single_play_reselection_eviction_and_call_cancellation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(animation.tk,'PhotoImage',side_effect=lambda **kw:kw['data']), patch.object(animation,'LIMIT',60000):
            directory=Path(tmp);photo=make_gif(directory)
            selected = {'id': 'one', 'photo': photo}
            app=SimpleNamespace(root=Root(),avatar=Canvas(),closed=False,setup_stage=None,settings_open=False,carousel_motion=None,
                portrait_animation_target=('one',64),model=SimpleNamespace(state=State.HOME,selected=selected,contacts=[selected]))
            player=animation.PortraitAnimation(app,directory)
            self.pump(player,lambda:player.completed==1)
            self.assertEqual(player.frame,1);self.assertEqual(app.avatar.photo,list(player.cache.values())[0][0][-1])
            paints=app.avatar.paints
            for _ in range(5):player.tick()
            self.assertEqual(player.completed,1);self.assertEqual(app.avatar.paints,paints)
            app.carousel_motion=True;player.tick();self.assertIsNone(player.key)
            app.carousel_motion=None
            self.pump(player,lambda:player.completed==2)
            app.portrait_animation_target=('one',65)
            self.pump(player,lambda:player.completed==3)
            self.assertEqual(len(player.cache),1)
            self.assertLessEqual(sum(x[2] for x in player.cache.values()),60000)
            app.model.state=State.IN_CALL;player.tick()
            self.assertFalse(player.cache);self.assertFalse(player.playing)
            self.assertEqual(player.error_count,0)
            player.close();app.closed=True;player.tick()

    def test_preload_prepares_other_contacts_before_selection_and_reuses_frames(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(animation.tk, 'PhotoImage', side_effect=lambda **values: values['data']) as photo_image, \
                patch.object(animation, 'load_frames', wraps=animation.load_frames) as decode:
            directory = Path(tmp)
            selected = {'id': 'initials', 'photo': ''}
            first = make_gif(directory)
            second = '/photos/late.gif'
            contacts = [selected, {'id': 'first', 'photo': first}, {'id': 'second', 'photo': second}]
            app = SimpleNamespace(
                root=Root(), avatar=Canvas(), closed=False, setup_stage=None, settings_open=False,
                carousel_motion=None, portrait_animation_target=('initials', 64),
                model=SimpleNamespace(state=State.HOME, selected=selected, contacts=contacts),
            )
            player = animation.PortraitAnimation(app, directory)
            self.pump(player, lambda: (first, 64) in player.preloaded and player.preload_retry_at)
            photo_image.assert_not_called()
            self.assertEqual(decode.call_count, 1)

            (directory / second.lstrip('/')).write_bytes((directory / first.lstrip('/')).read_bytes())
            self.pump(player, lambda: (second, 64) in player.preloaded)
            self.assertEqual(decode.call_count, 2)
            photo_image.assert_not_called()

            app.model.selected = contacts[1]
            app.portrait_animation_target = ('first', 64)
            self.pump(player, lambda: player.completed == 1)
            self.assertEqual(decode.call_count, 2)
            self.assertEqual(photo_image.call_count, 2)
            app.model.state = State.IN_CALL
            player.tick()
            self.assertFalse(player.preloaded)
            self.assertFalse(player.cache)
            self.assertEqual(player.error_count, 0)

    def test_preloaded_frames_keep_a_separate_bounded_budget(self):
        player = animation.PortraitAnimation(SimpleNamespace(root=Root()), Path('.'))
        first, second = ('/photos/a.gif', 64), ('/photos/b.gif', 64)
        player.preload_targets = (first, second)
        with patch.object(animation, 'PRELOAD_LIMIT', 8):
            for key in (first, second):
                player.results.put((key, ([b'frame', b'2'], [50, 50]), None))
                player.prepare()
        self.assertEqual(list(player.preloaded), [second])
        self.assertEqual(player.preload_attempted, {first, second})
        self.assertFalse(player.cache)
    def test_bounds_invalid_gif_and_missing_file_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);photo=make_gif(directory);path=directory/photo.lstrip('/')
            pngs,durations=animation.load_frames(path,64)
            self.assertEqual(len(pngs),2);self.assertEqual(durations,[50,50])
            with self.assertRaises(ValueError):animation.load_frames(path,10000)
            path.write_bytes(b'not a GIF')
            with self.assertRaises(ValueError):animation.load_frames(path,64)
            app=SimpleNamespace(root=Root())
            player=animation.PortraitAnimation(app,directory)
            player.request(('/photos/missing.gif',64))
            self.assertIsNone(player.loading);self.assertFalse(player.failures)

    def test_download_validation_rejects_excessive_frames_timing_and_dimensions(self):
        import io
        from PIL import Image
        from zmala_terminal.common.photo_cache import valid_photo
        for count, delay, size in [(1,100,480),(73,20,480),(2,3000,480),(3,2000,480),(2,100,479)]:
            frames=[Image.new('RGB',(size,size),(i*3,0,0)) for i in range(count)]
            out=io.BytesIO()
            frames[0].save(out,format='GIF',save_all=True,append_images=frames[1:],duration=delay)
            self.assertFalse(valid_photo(out.getvalue(),'untrusted.gif'),(count,delay,size))
