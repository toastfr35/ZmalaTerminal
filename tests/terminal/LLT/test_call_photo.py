# @test T-LLT-091
# @requirements LLR-TERM-VIDEO-020
# @environment portable
# @plan Decode bounded JPEGs and reject oversized/wrong-format images. Feed current/stale worker results and expired leases through recording Tk widgets; ensure call changes and stop remove photo state without media calls. Validate status field types, lease clamping and query encoding. Count downloads and decodes around expiry, reuse unchanged images and recover from worker-start failure. Keep request failures from renewing the displayed lease.
# @pass Pixels preserve their aspect ratio; stale results never display; clearing and expiry release the overlay without altering audio or video handles.
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from PIL import Image
from zmala_terminal.common.call_photo import CallPhoto, PhotoResult, decode_photo, fetch_photo
from zmala_terminal.common.model import State


class CallPhotoTests(unittest.TestCase):
    def test_bounded_decode(self):
        for fmt, size, valid in [('JPEG', (800, 400), True), ('PNG', (20, 20), False), ('JPEG', (1700, 2), False)]:
            output=io.BytesIO(); Image.new('RGB',size).save(output,fmt)
            if valid: self.assertEqual(decode_photo(output.getvalue()).size,size)
            else:
                with self.assertRaises(ValueError): decode_photo(output.getvalue())
        with self.assertRaises(ValueError): decode_photo(b'x'*(2097152+1))

    def fixture(self):
        root=Mock()
        with patch('zmala_terminal.common.call_photo.tk.Label'):
            view=CallPhoto(root)
        view.draw=Mock()
        engine=Mock(); engine.call_id.return_value='call'
        app=SimpleNamespace(engine=engine,configuration=Mock(),model=SimpleNamespace(state=State.IN_CALL,config={'call_photo_sharing':True}))
        view.owner=(engine,'call',app.configuration); view.next_poll=float('inf')
        return view,app

    def test_current_photo_then_expiry_and_stale_call_result(self):
        view,app=self.fixture(); image=Image.new('RGB',(80,40))
        view.results.put(PhotoResult(view.owner,1,image,100))
        with patch('zmala_terminal.common.call_photo.time.monotonic',return_value=10): view.tick(app)
        self.assertIs(view.image,image); view.layer.place.assert_called_once()
        with patch('zmala_terminal.common.call_photo.time.monotonic',return_value=101): view.tick(app)
        self.assertIsNone(view.image)
        view.results.put(PhotoResult(view.owner,1,image,1000)); app.model.state=State.HOME
        view.tick(app); self.assertIsNone(view.image)
        app.engine.end.assert_not_called(); app.engine.video.assert_not_called()

    def test_stop_snapshot_hides_overlay(self):
        view,app=self.fixture(); view.image=Image.new('RGB',(80,40));view.revision=1
        view.results.put(PhotoResult(view.owner,2,None,0));view.tick(app)
        self.assertIsNone(view.image);view.layer.place_forget.assert_called()

    def test_failed_request_preserves_old_deadline_then_expires(self):
        view, app = self.fixture()
        view.image = Image.new('RGB', (80, 40))
        view.revision, view.deadline = 1, 100
        view.results.put(PhotoResult(view.owner, failed=True))
        with patch('zmala_terminal.common.call_photo.time.monotonic', return_value=99):
            view.tick(app)
        self.assertIsNotNone(view.image)
        self.assertEqual(view.deadline, 100)
        with patch('zmala_terminal.common.call_photo.time.monotonic', return_value=100):
            view.tick(app)
        self.assertIsNone(view.image)

    def test_result_expired_before_ui_processing_never_displays(self):
        view, app = self.fixture()
        image = Image.new('RGB', (80, 40))
        view.results.put(PhotoResult(view.owner, 1, image, 100))
        with patch('zmala_terminal.common.call_photo.time.monotonic', return_value=100):
            view.tick(app)
        self.assertIsNone(view.image)
        view.layer.place.assert_not_called()
        view.draw.assert_not_called()

    def test_worker_start_failure_allows_later_retry_and_no_overlap(self):
        view, app = self.fixture()
        view.next_poll = 0
        with patch('zmala_terminal.common.call_photo.threading.Thread') as thread:
            thread.return_value.start.side_effect = RuntimeError('No worker available')
            with patch('zmala_terminal.common.call_photo.time.monotonic', return_value=10):
                view.tick(app)
            self.assertFalse(view.busy)
            thread.return_value.start.side_effect = None
            with patch('zmala_terminal.common.call_photo.time.monotonic', return_value=11):
                view.tick(app)
            self.assertTrue(view.busy)
            with patch('zmala_terminal.common.call_photo.time.monotonic', return_value=20):
                view.tick(app)
            self.assertEqual(thread.call_count, 2)


class PhotoWorkerTests(unittest.TestCase):
    def setUp(self):
        self.configuration = Mock()
        self.owner = (object(), 'call?with&reserved=', self.configuration)
        self.status = {'revision': 1, 'sharing': True, 'remaining_ms': 12000}
        output = io.BytesIO()
        Image.new('RGB', (80, 40)).save(output, 'JPEG')
        self.jpeg = output.getvalue()

    def fetch(self, status, times=(100, 100), revision=None, previous_image=None):
        self.configuration.request.reset_mock()
        self.configuration.request.side_effect = [json.dumps(status), self.jpeg]
        with patch('zmala_terminal.common.call_photo.time.monotonic', side_effect=times):
            return fetch_photo(self.owner, revision, previous_image, 100)

    def test_download_and_encoded_call_identity(self):
        result = self.fetch(self.status)
        self.assertFalse(result.failed)
        self.assertEqual(result.image.size, (80, 40))
        self.assertEqual(result.deadline, 112)
        route = '/api/call/photo?call_id=call%3Fwith%26reserved%3D'
        self.assertEqual(self.configuration.request.call_args_list[0].args, (route,))
        self.assertEqual(self.configuration.request.call_args_list[1].args,
                         (route + '&image=1&revision=1',))

    def test_malformed_status_does_not_request_pixels(self):
        invalid = [None, [], 'status', {}, self.status | {'sharing': 'false'}]
        for field in ('revision', 'remaining_ms'):
            invalid.extend(self.status | {field: value} for value in (None, True, 1.5, '1', []))
        invalid.append(self.status | {'revision': -1})
        for status in invalid:
            with self.subTest(status=status):
                result = self.fetch(status)
                self.assertTrue(result.failed)
                self.assertEqual(self.configuration.request.call_count, 1)

    def test_expired_status_skips_download(self):
        for status in (self.status | {'remaining_ms': 0}, self.status | {'remaining_ms': -1},
                       {'revision': 1, 'sharing': True}, self.status | {'sharing': False}):
            with self.subTest(status=status):
                result = self.fetch(status)
                self.assertFalse(result.failed)
                self.assertIsNone(result.image)
                self.assertEqual(self.configuration.request.call_count, 1)
        result = self.fetch(self.status, times=(112,))
        self.assertIsNone(result.image)
        self.assertEqual(self.configuration.request.call_count, 1)

    def test_expired_transfer_skips_decode(self):
        with patch('zmala_terminal.common.call_photo.decode_photo') as decoder:
            result = self.fetch(self.status, times=(100, 112))
        self.assertFalse(result.failed)
        self.assertIsNone(result.image)
        decoder.assert_not_called()
        self.assertEqual(self.configuration.request.call_count, 2)

    def test_unchanged_revision_reuses_pixels_and_caps_lease(self):
        previous = Image.new('RGB', (80, 40))
        result = self.fetch(self.status | {'remaining_ms': 20000}, revision=1, previous_image=previous)
        self.assertIs(result.image, previous)
        self.assertEqual(result.deadline, 112)
        self.assertEqual(self.configuration.request.call_count, 1)

    def test_unchanged_revision_without_pixels_downloads(self):
        result = self.fetch(self.status, revision=1)
        self.assertIsNotNone(result.image)
        self.assertEqual(self.configuration.request.call_count, 2)

    def test_network_and_decode_failures_are_failed_results(self):
        for replies in ([OSError('Offline')], [b'{'], [json.dumps(self.status), OSError('Offline')],
                        [json.dumps(self.status), b'not a jpeg']):
            with self.subTest(replies=replies):
                self.configuration.request.side_effect = replies
                with patch('zmala_terminal.common.call_photo.time.monotonic', return_value=100):
                    result = fetch_photo(self.owner, None, None, 100)
                self.assertTrue(result.failed)
                self.assertIsNone(result.image)
