"""Offline Tingwu administration. No credentials or task response URLs are published."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / '.tingwu'
KINDS = ('Transcription', 'AutoChapters', 'Summarization', 'MeetingAssistance', 'PptExtraction', 'TextPolish')

def polished_transcript(rows, paragraphs):
    """Accept only unambiguous contiguous source mappings; never drop original content."""
    positions = {}
    for i, row in enumerate(rows):
        positions.setdefault(row['id'], []).append(i)
    replacements, covered = {}, set()
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict): continue
        text = paragraph.get('FormalParagraphText')
        refs = paragraph.get('SentenceIds')
        if not isinstance(text, str) or not text.strip() or not isinstance(refs, list) or not refs: continue
        ids = [str(s) for s in refs]
        if len(set(ids)) != len(ids) or any(len(positions.get(s, [])) != 1 for s in ids): continue
        indices = sorted(positions[s][0] for s in ids)
        if indices != list(range(indices[0], indices[-1]+1)) or covered.intersection(indices): continue
        sources = [rows[i] for i in indices]
        if len({r['speaker'] for r in sources}) != 1: continue
        start, end = sources[0]['start'], sources[-1]['end']
        if start is None or end is None or end <= start: continue
        replacements[indices[0]] = dict(id='polished-' + str(indices[0]), text=text.strip(),
            speaker=sources[0]['speaker'], start=start, end=end,
            sourceSentenceIds=[r['id'] for r in sources], edited=True)
        covered.update(indices)
    if not replacements: return []
    return [replacements[i] if i in replacements else dict(row, sourceSentenceIds=[row['id']], edited=False)
            for i, row in enumerate(rows) if i in replacements or i not in covered]

def valid_id(value):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', value):
        raise ValueError('课时 ID 仅允许英文、数字、下划线和连字符')
    return value

def load_env():
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('\"\''))

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)

def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None

def normalize(raw):
    result = dict(transcript=[], keywords=[], summary='', chapters=[], speakers=[], questions=[], slides=[], mindMap=[])
    sentences = {}
    transcription = raw.get('Transcription', {}).get('Transcription', {})
    for paragraph in transcription.get('Paragraphs', []):
        grouped = {}
        for word in paragraph.get('Words', []):
            sid = str(word.get('SentenceId', paragraph.get('ParagraphId', '')))
            grouped.setdefault(sid, []).append(word)
        for sid, words in grouped.items():
            starts = [number(w.get('Start')) for w in words if number(w.get('Start')) is not None]
            ends = [number(w.get('End')) for w in words if number(w.get('End')) is not None]
            row = {'id': sid, 'speaker': '发言人 ' + str(paragraph.get('SpeakerId', '')), 'start': min(starts) if starts else None,
                   'end': max(ends) if ends else None, 'text': ''.join(w.get('Text', '') for w in words)}
            result['transcript'].append(row)
            sentences.setdefault(sid, row)
    result['transcript'].sort(key=lambda r: r['start'] if r['start'] is not None else float('inf'))
    result['transcriptPolished'] = polished_transcript(result['transcript'], raw.get('TextPolish', {}).get('TextPolish', []))
    summary = raw.get('Summarization', {}).get('Summarization', {})
    result['summary'] = summary.get('ParagraphSummary', '')
    result['speakers'] = [{'speaker': s.get('SpeakerName') or '发言人 ' + str(s.get('SpeakerId', '')), 'summary': s.get('Summary', '')}
                          for s in summary.get('ConversationalSummary', [])]
    for question in summary.get('QuestionsAnsweringSummary', []):
        refs = question.get('SentenceIdsOfQuestion', []) + question.get('SentenceIdsOfAnswer', [])
        starts = [sentences[str(s)]['start'] for s in refs if str(s) in sentences and sentences[str(s)]['start'] is not None]
        result['questions'].append({'question': question.get('Question', ''), 'answer': question.get('Answer', ''), 'start': min(starts) if starts else None})
    def mind(nodes, depth=0):
        if depth > 12: return []
        return [{'title': n.get('Title', ''), 'children': mind(n.get('Topic', []), depth+1)} for n in nodes]
    result['mindMap'] = mind(summary.get('MindMapSummary', []))
    result['keywords'] = raw.get('MeetingAssistance', {}).get('MeetingAssistance', {}).get('Keywords', [])
    result['chapters'] = [{'title': c.get('Headline', ''), 'summary': c.get('Summary', ''), 'start': number(c.get('Start')), 'end': number(c.get('End'))}
                          for c in raw.get('AutoChapters', {}).get('AutoChapters', [])]
    result['slides'] = [{'image': c.get('FileUrl', ''), 'summary': c.get('Summary', ''), 'start': number(c.get('Start')), 'end': number(c.get('End'))}
                        for c in raw.get('PptExtraction', {}).get('PptExtraction', {}).get('KeyFrameList', [])]
    return result

def api(method, path, body=None):
    load_env()
    keys = [os.environ.get(k) for k in ('ALIBABA_CLOUD_ACCESS_KEY_ID', 'ALIBABA_CLOUD_ACCESS_KEY_SECRET', 'TINGWU_APP_KEY')]
    if not all(keys): raise ValueError('请先填写根目录 .env 的三项听悟配置')
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcore.request import CommonRequest
    except ImportError:
        raise ValueError('请先安装 tools/requirements.txt 中的依赖') from None
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('tingwu.cn-beijing.aliyuncs.com')
    request.set_version('2023-09-30')
    request.set_protocol_type('https')
    request.set_method(method)
    request.set_uri_pattern(path)
    if body is not None:
        request.add_query_param('type', 'offline')
        request.add_header('Content-Type', 'application/json')
        body['AppKey'] = keys[2]
        request.set_content(json.dumps(body).encode('utf-8'))
    response = json.loads(AcsClient(keys[0], keys[1], 'cn-beijing').do_action_with_exception(request))
    if str(response.get('Code', '0')) != '0':
        raise ValueError('听悟请求失败，错误码：' + str(response.get('Code')))
    return response['Data']

def https_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('请提供有效的 HTTPS 文件地址')
    return value

def download(url):
    # Tingwu can return HTTP OSS links; request the same asset over TLS.
    if url.startswith('http://'): url = 'https://' + url[7:]
    https_url(url)
    with urlopen(url, timeout=90) as response:
        return response.read(), response.headers.get_content_type()

def submit(args):
    valid_id(args.id)
    path = PRIVATE / (args.id + '.json')
    if path.exists() and not args.retry:
        raise ValueError('该课时已有任务记录，请先运行 status 或 collect；确认需重新付费处理时才使用 --retry')
    if path.exists() and args.retry:
        old = read_json(path)
        state = api('GET', '/openapi/tingwu/v2/tasks/' + old['taskId'])
        if state['TaskStatus'] != 'FAILED':
            raise ValueError('仅允许失败任务使用 --retry，正在处理或已完成的任务请继续查询/收集')
    source = https_url(args.file_url)
    public = https_url(args.video_url)
    if urlparse(public).query:
        raise ValueError('--video-url 请使用无签名查询参数的长期公开视频地址')
    body = {'Input': {'FileUrl': source, 'SourceLanguage': args.language, 'TaskKey': args.id}, 'Parameters': {
        'Transcription': {'DiarizationEnabled': True, 'Diarization': {'SpeakerCount': 0}},
        'AutoChaptersEnabled': True, 'MeetingAssistanceEnabled': True, 'MeetingAssistance': {'Types': ['KeyInformation']},
        'SummarizationEnabled': True, 'Summarization': {'Types': ['Paragraph', 'Conversational', 'QuestionsAnswering', 'MindMap']},
        'PptExtractionEnabled': True, 'TextPolishEnabled': not getattr(args, 'no_text_polish', False)}}
    data = api('PUT', '/openapi/tingwu/v2/tasks', body)
    write_json(path, {'taskId': data['TaskId'], 'id': args.id, 'title': args.title, 'date': args.date, 'videoUrl': public,
                     'textPolishEnabled': body['Parameters']['TextPolishEnabled']})
    print('任务已提交并记录。稍后运行 status；完成后运行 collect。')

def collect(args, record, data):
    if data['TaskStatus'] != 'COMPLETED':
        raise ValueError('任务尚未完成，当前状态：' + data['TaskStatus'])
    raw, warnings = {}, []
    cache = PRIVATE / args.id
    for kind in KINDS:
        url = data.get('Result', {}).get(kind)
        if not url:
            if kind != 'TextPolish' or record.get('textPolishEnabled'):
                warnings.append(kind + ' 无结果')
            continue
        try:
            payload, _ = download(url)
            raw[kind] = json.loads(payload)
            write_json(cache / (kind + '.json'), raw[kind])
        except Exception:
            if kind == 'Transcription': raise ValueError('转写结果下载失败，请稍后重新 collect') from None
            warnings.append(kind + ' 下载失败，可重新 collect')
    if 'Transcription' not in raw: raise ValueError('缺少转写结果，本次不发布课程数据')
    output = normalize(raw)
    existing_path = ROOT / 'data' / (args.id + '.json')
    if existing_path.exists():
        existing = read_json(existing_path)
        if existing.get('transcriptPolishSource') == 'text-only':
            if existing.get('transcript') != output['transcript']:
                raise ValueError('转写内容已改变，为保护单独生成的整理稿，本次未覆盖课程数据；请先备份并核对')
            output['transcriptPolished'] = existing.get('transcriptPolished', [])
            output['transcriptPolishSource'] = 'text-only'
    if 'TextPolish' in raw and not output['transcriptPolished']:
        warnings.append('整理稿为空或无法对应原句，已保留原始转写')
    for slide in output['slides']:
        if not slide['image']: continue
        try:
            payload, content_type = download(slide['image'])
            extension = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}.get(content_type)
            if not extension: raise ValueError('非受支持图片类型')
            relative = Path('data') / 'assets' / args.id / (hashlib.sha256(payload).hexdigest()[:20] + extension)
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            slide['image'] = relative.as_posix()
        except Exception:
            slide['image'] = ''
            warnings.append('一张 PPT 图片下载失败，可重新 collect')
    output.update({k: record[k] for k in ('id', 'title', 'date', 'videoUrl')})
    output['status'] = 'partial' if warnings else 'ready'
    write_json(ROOT / 'data' / (args.id + '.json'), output)
    catalog_path = ROOT / 'data' / 'courses.json'
    catalog = read_json(catalog_path) if catalog_path.exists() else []
    entry = {k: record[k] for k in ('id', 'title', 'date')}
    entry['data'] = 'data/' + args.id + '.json'
    existing = next((i for i,c in enumerate(catalog) if c['id'] == args.id), None)
    if existing is None: catalog.append(entry)
    else: catalog[existing] = entry
    write_json(catalog_path, catalog)
    print('课程 JSON 和 PPT 图片已保存。请预览后发布 data/ 文件夹。')
    for warning in warnings: print('提示：' + warning)

def main():
    parser = argparse.ArgumentParser(description='听悟离线课程处理工具')
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('submit', help='创建付费分析任务（每课只需一次）')
    create.add_argument('--id', required=True)
    create.add_argument('--title', required=True)
    create.add_argument('--date', default='')
    create.add_argument('--file-url', required=True, help='听悟可下载的 HTTPS 视频链接')
    create.add_argument('--video-url', required=True, help='学生观看用长期公开 HTTPS 视频链接')
    create.add_argument('--language', default='cn', choices=['cn','en','auto','multilingual'])
    create.add_argument('--retry', action='store_true')
    create.add_argument('--no-text-polish', action='store_true', help='关闭口语书面化，仅保留原始转写')
    polish = commands.add_parser('polish', help='通过百炼单独整理已有课程文字，不处理视频')
    polish.add_argument('--id', required=True)
    polish.add_argument('--sample-seconds', type=int, help='仅输出开头若干秒的对照样例，不修改课程')
    polish.add_argument('--overwrite', action='store_true', help='备份后替换已有整理稿')
    for name in ('status', 'collect'):
        command = commands.add_parser(name)
        command.add_argument('--id', required=True)
    args = parser.parse_args()
    valid_id(args.id)
    if args.command == 'polish':
        from polish import run
        run(args)
    elif args.command == 'submit': submit(args)
    else:
        record = read_json(PRIVATE / (args.id + '.json'))
        data = api('GET', '/openapi/tingwu/v2/tasks/' + record['taskId'])
        if args.command == 'collect': collect(args, record, data)
        else:
            print('任务状态：' + data['TaskStatus'])
            if data['TaskStatus'] == 'FAILED': print('错误码：' + str(data.get('ErrorCode', '未知')))

if __name__ == '__main__':
    try: main()
    except (ValueError, FileNotFoundError) as error:
        print('错误：' + str(error), file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        # SDK exceptions may include signed URLs; do not echo their full contents.
        print('请求未完成（' + type(error).__name__ + '）。请检查网络和配置后重试查询；提交结果不明时先到听悟控制台核实，避免重复计费。', file=sys.stderr)
        sys.exit(1)
