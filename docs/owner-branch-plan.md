# 负责人分支 + 自动校验合并 方案

> 目标：每个负责人（及其 AI）只往**自己的分支**推，仓库自动校验、自动合并进 `main`；
> 生成文件（行动清单、监控数据）只由机器人在 `main` 上写，任何人不抢占 `main`。
> 状态：方案稿，待拍板后实施。

## 1. 现状与问题

| 现状 | 问题 |
| --- | --- |
| 10 个负责人（含其 AI）直接往 `ai4s-crawler` 的 `main` 推送 | 晚上高峰每分钟数个提交，`git push` 频繁非快进被拒；两边的机器人互相覆盖 |
| `reviews/monitor-data.json`、`reviews/*/actions/*.md` 由 `review-actions.yml` 在 `main` 上生成并提交 | 生成文件与人工提交在同一分支，rebase 必然冲突（今天连续 5 次推送失败就是这个原因） |
| 交接靠「下载当前行动清单」（`reviews/<年>/actions/<姓名>.md`） | 人/AI 要手动下载再上传，无法闭环 |
| 一个自动化账号（「AI4S monitor bot」）能直接改 `tools/`、`static/` 并推 `main` | 21:05–21:37 反复 Reapply/Revert，把王梦冉的统计口径改成了九格卡片，页面口径与全组不一致 |

## 2. 目标形态

```
个人分支 review/<owner>        main                     站点
┌──────────────────┐  校验   ┌──────────────────┐   部署  ┌──────────────┐
│ reviews/<年>/<账号>│ ─────► │ 机器人合并 + 生成 │ ─────► │ Pages 快照    │
│ 本人白名单内文件   │  自动   │ monitor-data.json │        │ 负责人分屏    │
│ + owner_status.py │  合并   │ actions/*.md      │        │ 上次更新      │
└──────────────────┘         └──────────────────┘        └──────────────┘
```

四条规则：

1. **写权限最小化**：每个分支只能改「属于这个负责人的文件」，越界即失败。
2. **生成文件单一写入者**：`monitor-data.json`、`owner-activity.json`、`actions/*.md` 只由机器人在 `main` 上写，个人分支出现这些文件一律判为越界。
3. **没人需要点合并**：校验通过即自动收集、自动 squash 合并；冲突/越界才退回给人处理。
4. **任务在本地自己算**：人不需要下载清单、不需要复制链接；本地分支上跑 `python tools/owner_status.py --json` 就知道今天该干什么，AI 只对一句「继续」负责（见 §4.4、§5）。

## 3. 分支与权限模型

### 3.1 分支命名

在 `reviews/owners.json` 的每个 owner 上加 `branch` 字段（CI 只认这个字段，不猜）：

| 负责人 | 分支 | 可写账号目录 |
| --- | --- | --- |
| 乔徐阳 | `review/qiaoxuyang` | `Roman100021` |
| 王婉婷 | `review/wangwanting` | `Blueblue1101` |
| 南耀笛 | `review/nanyaodi` | `nydiii` |
| 朱长昊 | `review/zhuchanghao` | `zch66883` |
| 李雪婷 | `review/lixueting` | `zch66883-lixueting` |
| 郝卓迪 | `review/haozhuodi` | `zch66883-haozhuodi` |
| 丁利军 | `review/dinglijun` | `dinglijun` |
| 陈晨 | `review/chenchen` | `chenchen052512` |
| 王梦冉 | `review/wangmengran` | `wangmengran8789` |
| 龙兆科 | `review/longzhaoke` | `AlearnerDL` |

共用目录（`lixueting-haozhuodi` 这类）在 `shared_accounts` 里声明：该目录由声明的两位负责人共同可写，冲突时人工介入。

### 3.2 白名单（校验器按分支反查 owner，再展开 accounts）

允许写：

- `reviews/<年>/<account>.json` —— 逐篇决策
- `reviews/<年>/<account>/**` —— 覆盖率、查漏表、交接说明等
- `reviews/<年>/feedback/<account>.json` —— 阶段反馈（issues / next_actions）
- `metadata/<自己分工的 venue>/<年>/**` —— 采集数据的定点修正（见 §3.3，按数据规则单独校验）

一律禁止（机器人或管理员专属）：

- `reviews/monitor-data.json`、`reviews/owner-activity.json`
- `reviews/<年>/actions/**`、`reviews/owners.json`、`reviews/venue-review*.csv`、`reviews/source-assignments-*.json`、`monitor-feedback-format.md`
- `tools/**`、`static/**`、`*.html`、`.github/**`（今天王梦冉的自动化就是在改这些）

### 3.3 `metadata/` 不是禁止，是「按分工限定 + 数据规则校验」

**先澄清「最后怎么合并」：不需要谁去汇总。** `main` 上由机器人统一重建所有派生数据——

```
main 的 metadata/ + reviews/
      ↓ build_review_monitor.py / build_paper_index.py / build_owner_activity.py / generate_review_actions.py
reviews/monitor-data.json、data/papers-index.json、reviews/owner-activity.json、reviews/*/actions/*.md
      ↓ pages.yml
站点
```

也就是说：各人把自己的修改送进 `main`，派生数据的「合并」是 CI 每次重建时自动完成的，不存在人工合并这一步。

`metadata/` 的修改走同一个分支、同一套自动合并，但校验换成数据规则：

| 规则 | 说明 |
| --- | --- |
| 范围 | 只能改 `metadata/<code>/<年>/**`，`<code>` 必须在该负责人当年的 `source-assignments` 分工内 |
| 主键不可变 | 不允许改 `id`、`venue`、`year`；只允许补字段或增记录 |
| 只增不删 | 删除条数 > 0 直接判失败（要删必须人工 PR） |
| 证据字段 | 新增或修改的记录必须带 `provenance: {by, at, method, url}`，否则失败 |
| 体量 | 单次 PR 新增记录数上限（默认 3000 条）；`papers.json` 是 LFS，单次增量 > 100MB 拒绝 |
| 并存 | 同一 `metadata/<code>/<年>/*.json` 被两个人同时改 → 不自动合并，转人工 |
| 事后 | 合并后机器人重建派生物，`build_paper_index.py` 失败则回滚该 squash commit |

这样「补摘要」「补漏采论文」「修正年份或文献类型」都能自动进 `main`，但不会出现悄无声息地删数据、改主键、改别人 venue 的情况。

#### 摘要只有一个正本，副本不允许被清空

`metadata/<年>/ai4s.json` 里的 `abstract` 是 `papers.json` 的副本。`papers.json` 每年约 600MB 且走 LFS，CI 拉不下来，所以监控只能读 `ai4s.json` 里的这份副本。

2026-11-10 00:01 的 `99112db`（「回填候选摘要并标记已排除候选」）用 `papers.json` 重建了一次 `ai4s.json`，把 113 条已经回填好的摘要重置成 `null` 并标成 `needs_abstract`（乔徐阳 64 条、丁利军 49 条），监控随即把做过的活报成「AI4S候选缺少摘要」。

对策两条，已落地：

| 机制 | 位置 | 作用 |
| --- | --- | --- |
| 自动恢复 | `tools/restore_abstracts.py`，由爬虫 `review-actions.yml` 每次生成前调用 | 拿上一版 `main` 对比，只把「原本有、现在空」的摘要和对应 `screening_status` 补回来，其余字段一个字节不动 |
| 人工修复入口 | 同一脚本 `--owner <姓名>` | 需要只修某人的 venue 时手动跑，例如补回丁利军那 49 条 |

规则写进协作约定：**摘要只增不删**。确实需要清空某条错误摘要时，必须走人工 PR 并在描述里说明是哪条、为什么。

## 4. 新增的机器部件

### 4.1 `tools/validate_owner_changes.py`（本地与 CI 同一份代码）

```
python tools/validate_owner_changes.py \
    --owner 乔徐阳            # 或 --branch review/qiaoxuyang
    --base origin/main \
    --json                    # 机器可读输出，AI 直接读
```

返回 0/1，`--json` 输出：

```json
{
  "owner": "乔徐阳",
  "accounts": ["Roman100021"],
  "ok": false,
  "violations": [
    {"path": "reviews/monitor-data.json", "kind": "out_of_scope",
     "message": "生成文件只能由机器人在 main 上写"}
  ],
  "sources": {"delivered": 35, "total": 35, "pending": 0},
  "warnings": ["reviews/2024/Roman100021.json 与当前采集快照不一致"]
}
```

校验项：

1. 变更路径全部落在白名单内；
2. `reviews/<年>/<account>.json` 可解析，条目含 `id`/`venue`/`ai4s_review`，`decision ∈ {include, exclude, pending, unreviewed}`，同文件 `id` 不重复；
3. `venue` 必须在该负责人当年的分工范围内（读 `reviews/source-assignments-<年>.json`）；
4. `feedback/<account>.json` 的 `owner` = 本人、`github_username` = 本分支账号、`issues`/`next_actions` 为字符串数组；
5. 只读统计（交付来源数、待定数、缺摘要数）写进输出，供 AI 判断还差多少。

### 4.2 `review-validate.yml`（爬虫仓库，触发于 `review/**`）

```yaml
on:
  push:
    branches: ['review/**']
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v6
        with: { python-version: '3.12' }
      - name: Validate owner changes
        run: |
          python tools/validate_owner_changes.py \
            --branch "${{ github.head_ref || github.ref_name }}" \
            --base origin/main --json > "$RUNNER_TEMP/validate.json" || true
          python - <<'PY'
          # 把 violations 逐条输出成 ::error:: annotations，并把统计写进 ::notice::
          PY
      - uses: actions/upload-artifact@v4
        with: { name: owner-status, path: ${{ runner.temp }}/validate.json }
```

失败信息必须精确到 `文件:字段`，例如
`::error file=reviews/2024/Roman100021.json::第 812 条 venue=cikm 不属于本人分工范围`。

### 4.3 `review-merge.yml`（爬虫仓库，无人值守）

触发：`workflow_run`（validate 完成）、`schedule: '*/15 * * * *'`、`workflow_dispatch`。
`concurrency: { group: review-merge, cancel-in-progress: false }`。

每个 `review/**` 分支：

1. 取该分支最近一次 `validate` 结论，非 success → 跳过；
2. `git diff --name-only origin/main...origin/<branch>`，复核白名单（不信任上一次校验的时效）；
3. 无冲突 → 创建 PR（标题 `review: <姓名> <年> 第 N 批`）→ 用 App token 自动 approve → **squash merge**；
4. 有冲突或越界 → 保留分支，PR 标 `needs-owner-fix`，annotation 列出冲突文件；
5. 合并完成后（同一 workflow 内串行）跑生成器并提交到 `main`：
   `build_owner_activity.py` → `build_review_monitor.py` → `generate_review_actions.py`；
   机器人是 `main` 上生成文件的唯一写入者，这里不会再出现两边抢同一文件的冲突。

### 4.4 任务不自带链接，本地自己算：`tools/owner_status.py`

**不搞「复制任务说明」按钮，也不提交任务清单文件。** 每个人的本地检出本身就带着自己分支的全部分支信息和数据，任务由脚本从**本地工作树**算出来，AI 不需要下载、人不需要复制。

```
python tools/owner_status.py            # 人看的摘要
python tools/owner_status.py --json     # AI 读的结构化任务
```

脚本做的事：

1. `git branch --show-current` → 若不是 `review/<owner>` 就报错并提示该切到哪条分支（不会静默猜）；
2. 从 `reviews/owners.json` 取该负责人与账号，从 `reviews/source-assignments-<年>.json` 取分工；
3. 按 `reviews/<年>/<账号>.json` 的本地内容算每个来源：有没有逐篇交付、待定多少、缺摘要多少、官网同口径总数确认没有、快照是否过期、同论文判定是否冲突；
4. 输出任务列表，每条都带**该写到哪个文件**：

```json
{
  "owner": "乔徐阳", "account": "Roman100021", "branch": "review/qiaoxuyang",
  "behind": false,
  "years": {
    "2024": {"sources": 35, "delivered": 35, "pending": 0, "status": "complete"},
    "2025": {"sources": 35, "delivered": 3, "pending": 12, "status": "in_progress"}
  },
  "tasks": [
    {"year": 2025, "code": "iclr", "kind": "no_delivery",
     "message": "2025 年尚无逐篇交付", "write_to": ["reviews/2025/Roman100021.json"]},
    {"year": 2025, "code": "acl", "kind": "pending_decisions",
     "message": "12 篇仍为待定", "write_to": ["reviews/2025/Roman100021.json"]}
  ]
}
```

为避免三处逻辑漂移，`build_review_monitor.py`、`owner_status.py`、`validate_owner_changes.py` 共用一个新模块 `tools/review_model.py`（来源加载、单来源分析、状态判定）。

### 4.5 `AGENTS.md`（让 AI 自动读到规矩，不用人解释）

爬虫仓库根目录放 `AGENTS.md`（主流 AI 编程助手会自动读），内容固定：

```md
# 本仓库的审核协作约定
1. 开工前先跑 `python tools/owner_status.py --json`，它按当前分支告诉你负责人身份和未完成任务。
2. 只改白名单内的文件：`reviews/<年>/<你的账号>.json`、`reviews/<年>/<你的账号>/**`、
   `reviews/<年>/feedback/<你的账号>.json`。其他一律不改。
3. 不要修改生成文件（monitor-data.json、actions/、owner-tasks 等），它们在 main 上由机器人维护。
4. 提交前跑 `python tools/validate_owner_changes.py --json`，必须返回 0。
5. 只 push 当前分支 `review/<owner>`，不要 push main。
```

## 5. 负责人 AI 的日常（人只需要说一句「继续」）

一次性准备（每人只做一次）：

```bash
git clone https://github.com/BUPT-AI4S/ai4s-crawler && cd ai4s-crawler
git switch review/qiaoxuyang        # 之后长期停在这条分支
```

之后每个会话，人只对 AI 说「继续」，AI 顺序执行：

```bash
git pull --rebase                     # 拿到别人合并的新数据和最新分工
python tools/owner_status.py --json   # 自己算今天该干什么
# … 干活，只动白名单文件 …
python tools/validate_owner_changes.py --json   # 本地预检，同 CI 代码
git add reviews/<年>
git commit -m "2025 精筛：补录 iclr 等 3 个来源"
git push origin review/<owner>        # 校验通过 → 自动合入 main
```

没有下载、没有复制、没有点合并；失败信息以 check-run annotation 和 `owner_status.py` 的 `tasks` 回到同一台机器上，AI 自己接着改。

明确禁止：改生成文件、改 `tools/`、改别人目录、直接推 `main`、在本地跑生成器（生成物由 CI 产出，本地跑了会产生脏文件）。

## 6. 迁移计划（每阶段可独立停下）

| 阶段 | 内容 | 预估 | 可回退 |
| --- | --- | --- | --- |
| P0 | `owners.json` 加 `branch` 字段；写 `validate_owner_changes.py` + 单测；对 `main` 现状跑一遍应零越界 | 0.5 天 | 纯新增文件 |
| P1 | 上线 `review-validate.yml`；为 10 人建 `review/<owner>` 分支（基于当前 main）；分支保护只对 `review/**` 开校验 | 0.5 天 | 删除 workflow |
| P2 | `review_model.py` + `owner_status.py` + `AGENTS.md`；站点负责人分屏只保留汇总数字（不加复制按钮）；md 行动清单继续生成，供人看 | 0.5 天 | 删除脚本 |
| P3 | `review-merge.yml` 先 dry-run 72 小时（只写汇总不合并），确认无越界误报后开启真合并 | 1 天 | 关闭 workflow |
| P4 | 开 `main` 保护：只允许 bot push，人类一律走分支；通知各人与其 AI 改推送目标；观察一周后把 md 下载入口降级为「可选」 | 0.5 天 | 放宽保护规则 |

## 7. 风险与对策

| 风险 | 对策 |
| --- | --- |
| 自动合并把错误数据带进 `main` | 校验先于合并；只合并本人白名单；合并后若发现坏数据，`git revert` 单个 squash commit 即可 |
| 负责人 AI 误改别人的文件或生成文件 | 校验判越界并拒绝合并，annotation 精确到文件 |
| 共用账号目录（zch66883-lixueting 等）双方同时改 | `shared_accounts` 声明共写；CI 冲突时退回人工，不自动覆盖 |
| 分支长期落后 `main` | 机器人每 15 分钟 rebase 并重推；冲突只可能出现在自己改过的文件 |
| 又出现「AI4S monitor bot」这类直接改工具/页面的账号 | `main` 保护 + token 权限收紧；`tools/**`、`static/**` 不在任何个人分支白名单内，只能人工 PR |
| 大文件（LFS 的 `metadata/*/papers.json`）被误推 | 只允许改自己分工内 venue；单次增量上限；超过转人工 |
| 有人在 `metadata/` 里删数据或改主键 | 校验规则：只增不删、主键不可变、必须带 `provenance`，失败即不合并 |
| 站点快照滞后 | 合并即触发 push → Pages 重建；每小时 cron 兜底（已生效） |

## 8. 需要拍板的三件事

1. **自动合并方式**：机器人自动 approve 后 squash merge（有 PR 审计记录，推荐）/ 直接 push 到 `main`（最快，无记录）。
2. **`metadata/` 的修改规则**：推荐「允许改自己分工内的 venue + 数据规则校验」（§3.3），而不是一刀切禁止；要更严就改成只能通过爬虫脚本产出的 PR。
3. **`main` 是否真正锁死**：推荐只允许机器人推送，人类一律走 `review/<owner>`（否则「不抢占 main」只是口头约定）。

## 9. 涉及文件清单

新增：

- `tools/review_model.py`（来源加载、单来源分析、状态判定，三个脚本共用）
- `tools/validate_owner_changes.py`、`tests/test_validate_owner_changes.py`
- `tools/owner_status.py`、`tests/test_owner_status.py`
- `.github/workflows/review-validate.yml`、`.github/workflows/review-merge.yml`（爬虫仓库）
- `AGENTS.md`（爬虫仓库根目录，AI 自动读取的协作约定）

修改：

- `reviews/owners.json`（加 `branch`）
- `.gitignore`（忽略 `owner_status.py --write` 的本地输出，如 `owner-status.local.json`）
- `.github/workflows/review-actions.yml`（去掉与个人提交竞争的逻辑，只保留 `main` 生成，或在 review-merge 里统一调用）
- 站点 `static/js/review-monitor.mjs`（负责人分屏保持汇总数字，不加复制按钮；md 清单入口保留但不作为必经步骤）
