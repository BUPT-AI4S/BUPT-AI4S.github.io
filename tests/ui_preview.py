"""Manual UI regression fixture server, isolated from published course data.
Run python tests/ui_preview.py, then visit http://localhost:8081/replay.html.
"""
import json
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from preview import Handler

COURSE = {'id':'fixture','title':'交互测试课（非真实内容）','date':'2026-09-26','videoUrl':'','status':'ready',
 'transcript':[{'speaker':'测试讲者','start':0,'end':1000,'text':'科学智能与科学智能实践。'}, {'speaker':'测试讲者','start':2000,'end':3000,'text':'用证据理解模型。'}],
 'keywords':['科学智能'],'summary':'测试概要 A',
 'chapters':[{'title':'测试章节','start':0,'summary':'章节说明'}],
 'speakers':[{'speaker':'测试讲者','summary':'发言说明'}],
 'questions':[{'question':'如何验证？','answer':'依据证据。','start':0}],
 'slides':[{'image':'static/images/favicon.svg','summary':'测试课件（用图标验证图片显示）','start':None}],
 'mindMap':[{'title':'测试根节点','children':[{'title':'子节点 A','children':[]}]}]}
CATALOG=[{'id':'fixture','title':COURSE['title'],'data':'data/fixture.json'}, {'id':'missing','title':'加载失败测试课','data':'data/missing.json'}]

class FixtureHandler(Handler):
    def do_GET(self):
        data={'/data/courses.json':CATALOG,'/data/fixture.json':COURSE}.get(self.path)
        if data is None: return super().do_GET()
        payload=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)

if __name__=='__main__':
    port=int(sys.argv[1]) if len(sys.argv)>1 else 8081
    print(f'UI fixtures: http://localhost:{port}/replay.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),FixtureHandler).serve_forever()
