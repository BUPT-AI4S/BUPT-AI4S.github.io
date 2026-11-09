"""Write owner-specific, traceable action files into a crawler checkout."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote


def write_actions(data, review_root):
    review_root = Path(review_root)
    written = []
    for year in data['years']:
        by_owner = defaultdict(list)
        for source in year['sources']:
            if source['owner']:
                by_owner[source['owner']].append(source)
        for owner, sources in sorted(by_owner.items()):
            name = re.sub(r'[^\w\u4e00-\u9fff.-]', '_', owner).strip('.')
            if not name or name in ('.', '..'): raise ValueError('Invalid owner filename')
            path = review_root / str(year['year']) / 'actions' / (name + '.md')
            path.parent.mkdir(parents=True, exist_ok=True)
            lines = [f"# {year['year']} 论文审核行动清单：{owner}", '',
                '> 自动汇总的工作提示，具体处理以负责人核验及原始证据为准。请勿直接编辑本文件。', '',
                f"- 输入仓库提交：`{data.get('commit') or '未知'}`",
                f"- 采集快照：`{year.get('captured_at') or '未知'}`",
                '- 反馈格式：[阶段反馈说明](../../../monitor-feedback-format.md)',
                '- 先拉取最新仓库和词表，确认分工及快照；完成后提交逐篇审核和阶段反馈。', '']
            for s in sources:
                lines += [f"## {s['title']}（{s['code']}）", '',
                    '问题：' + ('；'.join(s['issues']) if s['issues'] else '暂无自动提示，仍需检查原始报告。'), '',
                    '下一步：' + ('；'.join(s['actions']) if s['actions'] else '核对原始材料并按需反馈。'), '']
                if s['files']:
                    lines.append('原始交付：' + '；'.join('[文件](' + data['repository'] + '/'.join(quote(part) for part in f.split('/')) + ')' for f in s['files']))
                    lines.append('')
            path.write_text('\n'.join(lines).rstrip()+'\n', encoding='utf8')
            written.append(path)
    return written


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--input',type=Path,required=True); parser.add_argument('--reviews',type=Path,required=True); args=parser.parse_args()
    data=json.loads(args.input.read_text(encoding='utf8')); files=write_actions(data,args.reviews)
    print(f'Wrote {len(files)} owner action files')

if __name__ == '__main__': main()
