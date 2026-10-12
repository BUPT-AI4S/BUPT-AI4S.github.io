# C-FREE 完整添加案例

测试日期：2026-10-12。论文为 [Learning the Neighborhood: Contrast-Free Multimodal Self-Supervised Molecular Graph Pretraining](https://proceedings.mlr.press/v306/ariguib26a.html)，ICML 2026，PMLR 306:3452–3472。本次测试的是论文入库流程，没有运行论文的模型训练。

## 查词表与登记

先执行 `python tools/manage_paper_tags.py list --query graph`。添加前本地词表共 5 项，没有图神经网络标签；已有 `pretraining` 可以复用。

在 [CSO 3.5 官方 CSV](https://cso.kmi.open.ac.uk/download/version-3.5/CSO.3.5.csv.zip) 中核实了以下概念与英文名称：

```text
https://cso.kmi.open.ac.uk/topics/graph_neural_networks
graph neural networks
```

“图神经网络”描述模型方法，“预训练”描述训练阶段，两者不是同义词。通过登记工具添加新标签：

```sh
python tools/manage_paper_tags.py add --id graph-neural-networks --en "Graph neural networks" --zh "图神经网络" --alias GNN --alias GNNs --alias "Graph neural network" --description "针对图结构学习节点、边或整图表示的神经网络；与训练阶段标签预训练区分。" --source "https://cso.kmi.open.ac.uk/topics/graph_neural_networks"
```

登记后词表有 6 项，使用 `list --query GNN` 能查到新标签。这个命令是本次已执行的登记记录，复查已有标签使用 `list`，不要重复执行 `add`。

## 创建论文目录

```text
data/papers/c-free/
├── paper.md
└── images/
    ├── architecture.png
    └── results.png
```

[paper.md](../data/papers/c-free/paper.md) 包含真实标题、三位作者、论文中列出的单位、ICML 2026、AI for 化学分类、完整英文原摘要及中文译文、关键词、资源链接和中英文解读。

标签引用为 `tags: [pretraining, graph-neural-networks]`。官方代码链接为 [ariguiba/C-FREE](https://github.com/ariguiba/C-FREE)。

`architecture.png` 来自正式 PDF 第 3 页的 Figure 1；`results.png` 来自第 6 页的 Table 2。两张图都保留原英文图注，在 Markdown 中用 `images/文件名` 引用，并注明作者、来源和许可。未用自绘示意图替代原图。

中文和英文解读各有八个章节。引用的实验数值包括 Table 2 的 C-FREE PaiNN 平均 ROC-AUC 79.81、UniMol 78.56，以及不同数据集上的反例；正文区分冻结探测、全量微调及不同指标。

## 验证结果

对本次真实论文目录，在独立临时工作区执行了以下检查：

| 检查 | 结果 |
| --- | --- |
| 删除新标签后尝试构建 | 未登记标签被拒绝，原索引保持不变 |
| 通过实际登记命令加入新标签 | 成功，重新构建可识别 |
| 重复登记同一 ID | 被拒绝，词表文件保持不变 |
| 同时使用 `GNN`、`GNNs` 和规范 ID | 自动归一并去重为一个图神经网络标签 |
| 图神经网络标签论文数 | 1，重复别名没有增加计数 |
| 原摘要与中文译文 | 均进入目录索引 |
| 中英文详情 | 各八个章节，数值和代码链接保留 |
| 发布产物 | 正文源文件、详情数据和两张原图均进入 `_site/` |

仓库根目录的实际构建命令：

```sh
python tools/build_paper_index.py --site
python -m unittest discover -s tests
node --test tests/papers.test.mjs tests/replay.test.mjs
```

## 页面验收

目录页按“图神经网络”筛选应显示 C-FREE 一篇；“预训练”关联 ClimaX 和 C-FREE 两篇。卡片独立切换中英文摘要；详情页显示原图、图注、来源与官方代码链接。

提交时同时包含论文目录和词表，本次还包含此前已验证的逐篇目录迁移及统一标签功能。发布结果通过同次提交的 GitHub Actions 和线上页面核对。
