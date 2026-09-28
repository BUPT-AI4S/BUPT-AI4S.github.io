"""Loopback-only static preview with a mapped local video and HTTP range support."""
import argparse
import io
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]

def configure_videos(root, course_id=None, video=None):
    catalog = json.loads((root / 'data/courses.json').read_text(encoding='utf-8'))
    ids = {c['id'] for c in catalog}
    registry = root / '.tingwu/preview-videos.json'
    saved = json.loads(registry.read_text(encoding='utf-8')) if registry.exists() else {}
    saved = {key: value for key, value in saved.items() if key in ids}
    if video is not None:
        if course_id not in ids:
            raise ValueError('请用 --id 指定课程目录中存在的课时 ID')
        if not video.is_file():
            raise ValueError('视频文件不存在')
        saved[course_id] = str(video.resolve())
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    return {key: Path(value) for key, value in saved.items()}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, videos=None, **kwargs):
        self.videos = videos or {}
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        path = unquote(urlparse(self.path).path)
        if any(p.startswith('.') for p in Path(path).parts) or path.startswith(('/tools/', '/tests/')):
            self.send_error(404)
            return None
        self.range_end = None
        local = re.fullmatch(r'/data/([^/]+)\.local\.json', path)
        if local:
            course_id = local[1]
            if course_id not in self.videos:
                self.send_error(404)
                return None
            body = json.dumps({'videoUrl': f'/local-video/{course_id}.mp4'}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return io.BytesIO(body)
        if not path.startswith('/local-video/'): return super().send_head()
        media = re.fullmatch(r'/local-video/([^/]+)\.mp4', path)
        video_path = self.videos.get(media[1]) if media else None
        if not video_path or not video_path.is_file():
            self.send_error(404)
            return None
        size = video_path.stat().st_size
        start, end, code = 0, size-1, 200
        header = self.headers.get('Range')
        if header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', header)
            if not match or not any(match.groups()):
                self.send_error(416)
                return None
            a,b = match.groups()
            if a: start, end = int(a), min(int(b),size-1) if b else size-1
            else: start = max(0,size-int(b))
            if start > end or start >= size:
                self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers()
                return None
            code = 206
        self.send_response(code)
        self.send_header('Content-Type','video/mp4')
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(end-start+1))
        if code == 206: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        file = video_path.open('rb'); file.seek(start)
        self.range_end = end-start+1
        return file

    def copyfile(self, source, outputfile):
        if self.range_end is None: return super().copyfile(source, outputfile)
        remaining = self.range_end
        try:
            while remaining:
                chunk = source.read(min(1024*1024,remaining))
                if not chunk: break
                outputfile.write(chunk); remaining -= len(chunk)
        except (ConnectionError, BrokenPipeError): pass

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--video',type=Path)
    parser.add_argument('--id', help='绑定视频的课时 ID，例如 chairs-01')
    parser.add_argument('--port',type=int,default=8080)
    args=parser.parse_args()
    try:
        videos = configure_videos(ROOT, args.id, args.video)
    except ValueError as error:
        parser.error(str(error))
    print(f'Preview: http://localhost:{args.port}/replay.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,videos=videos)).serve_forever()
