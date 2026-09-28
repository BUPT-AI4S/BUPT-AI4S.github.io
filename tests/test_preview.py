import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from preview import Handler, configure_videos

class QuietHandler(Handler):
    def log_message(self, *args): pass

class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        video = Path(cls.temp.name) / 'test.mp4'
        video.write_bytes(b'0123456789')
        other = Path(cls.temp.name) / 'other.mp4'
        other.write_bytes(b'abcdefghij')
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, videos={'lecture-01': video, 'chairs-01': other}))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup()

    def test_partial_video_and_suffix(self):
        for requested, expected, span in [('bytes=2-5',b'2345','bytes 2-5/10'),('bytes=-3',b'789','bytes 7-9/10')]:
            with self.subTest(requested=requested), urlopen(Request(self.url+'/local-video/lecture-01.mp4',headers={'Range':requested})) as res:
                self.assertEqual(res.status,206)
                self.assertEqual(res.headers['Content-Range'],span)
                self.assertEqual(res.read(),expected)

    def test_out_of_range(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.url+'/local-video/lecture-01.mp4',headers={'Range':'bytes=50-'}))
        self.assertEqual(caught.exception.code,416)

    def test_independent_courses(self):
        import json
        for course, expected in [('lecture-01', b'0123'), ('chairs-01', b'abcd')]:
            with urlopen(self.url + '/data/' + course + '.local.json') as res:
                route = json.load(res)['videoUrl']
            with urlopen(Request(self.url + route, headers={'Range':'bytes=0-3'})) as res:
                self.assertEqual(res.read(), expected)
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.url + '/local-video/chair-01.mp4')
        self.assertEqual(caught.exception.code, 404)

    def test_persisted_bindings(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'data').mkdir()
            (root/'data/courses.json').write_text(json.dumps([{'id':'lecture-01'}, {'id':'chairs-01'}]))
            first, second = root/'first.mp4', root/'second.mp4'
            first.write_bytes(b'first'); second.write_bytes(b'second')
            configure_videos(root, 'lecture-01', first)
            configure_videos(root, 'chairs-01', second)
            self.assertEqual(configure_videos(root), {'lecture-01':first, 'chairs-01':second})
            with self.assertRaises(ValueError): configure_videos(root, None, second)
            with self.assertRaises(ValueError): configure_videos(root, 'chair-01', second)

    def test_private_paths_are_not_served(self):
        for path in ['/.env','/.git/config','/.tingwu/test.json','/tools/tingwu.py']:
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(self.url+path)
            self.assertEqual(caught.exception.code,404)
