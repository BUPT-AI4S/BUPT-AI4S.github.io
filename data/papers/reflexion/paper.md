---
id: '2303.11366'
title: 'Reflexion: Language Agents with Verbal Reinforcement Learning'
titleZh: Reflexion：通过语言反馈改进智能体
authors:
- Noah Shinn
- Federico Cassano
- Edward Berman
- Ashwin Gopinath
- Karthik Narasimhan
- Shunyu Yao
published: '2023-03-20'
venue: arXiv
topics:
- agents
- reasoning
sample: true
summaryZh: 让智能体把任务反馈写成反思文本，保存在记忆中，并用于下一次尝试。无需更新模型权重，探索从试错中改进决策的路径。
summaryEn: |-
  Agents turn task feedback into reflective text, retain it in episodic memory, and use it in subsequent attempts without updating model weights.
paperUrl: https://arxiv.org/abs/2303.11366
pdfUrl: https://arxiv.org/pdf/2303.11366
disciplines:
- general
subfield: 通用智能体方法
year: '2023'
decision: ''
keywords:
- Language agents
- Verbal feedback
- Episodic memory
classificationReason: 这篇研究不限定具体学科的通用智能体方法，因此归入通用 AI；智能体和推理作为方法标签。
notesMeta:
  templateVersion: '1.0'
  generated: ''
  reviewed: false
  basisZh: 已有概述，尚未进行全文核对。
  basisEn: Existing summary; full paper not checked.
  sources: []
affiliations: []
codeUrl: ''
tags:
- agents
- reasoning
abstract: |-
  Large language models (LLMs) have been increasingly used to interact with external environments (e.g., games, compilers, APIs) as goal-driven agents. However, it remains challenging for these language agents to quickly and efficiently learn from trial-and-error as traditional reinforcement learning methods require extensive training samples and expensive model fine-tuning.

  We propose Reflexion, a novel framework to reinforce language agents not by updating weights, but instead through linguistic feedback. Concretely, Reflexion agents verbally reflect on task feedback signals, then maintain their own reflective text in an episodic memory buffer to induce better decision-making in subsequent trials.

  Reflexion is flexible enough to incorporate various types (scalar values or free-form language) and sources (external or internally simulated) of feedback signals, and obtains significant improvements over a baseline agent across diverse tasks (sequential decision-making, coding, language reasoning). For example, Reflexion achieves a 91% pass@1 accuracy on the HumanEval coding benchmark, surpassing the previous state-of-the-art GPT-4 that achieves 80%.

  We also conduct ablation and analysis studies using different feedback signals, feedback incorporation methods, and agent types, and provide insights into how they affect performance.
abstractZh: |-
  大型语言模型（LLM）越来越多地被用作以目标为导向的智能体，与外部环境（例如游戏、编译器和 API）交互。然而，这些语言智能体仍然难以快速、高效地从试错中学习，因为传统强化学习方法需要大量训练样本和昂贵的模型微调。

  我们提出 Reflexion，一种通过语言反馈而非更新模型权重来强化语言智能体的新框架。具体而言，Reflexion 智能体以语言形式反思任务反馈信号，并将生成的反思文本保存在情节记忆缓冲区中，以促进后续尝试中的更好决策。

  Reflexion 可以灵活整合不同类型（标量值或自由形式的语言）和不同来源（外部提供或内部模拟）的反馈信号，并在多种任务（序列决策、编程和语言推理）上相较基线智能体取得显著提升。例如，Reflexion 在 HumanEval 编程基准上取得 91% 的 pass@1 准确率，超过此前达到 80% 的先进模型 GPT-4。

  我们还使用不同的反馈信号、反馈整合方法和智能体类型开展消融与分析研究，探讨它们如何影响性能。
abstractSource: https://arxiv.org/abs/2303.11366v4
abstractLicense: https://creativecommons.org/licenses/by/4.0/
translationSource: 英文摘要保留原文；中文为依据原摘要逐段翻译，未经人工审核。
---

## 研究问题

语言智能体如何在不进行昂贵微调的情况下，从任务失败和外部反馈中学习？

## 核心方法

将标量或文字形式的反馈转化为语言反思，存入情节记忆，并在后续尝试中作为上下文使用。

## 结果与证据

论文摘要报告了序列决策、编程和语言推理任务上的改进。具体实验设置、基线与消融请参阅原文；此处不将结果外推至科学发现任务。

## 阅读边界

用于 AI4S 时，仍需验证反馈是否可靠、任务能否重复执行，以及反思内容是否有效。

<!-- language: en -->

## Problem

How can language agents learn from failures and feedback without costly fine-tuning?

## Method

Convert scalar or textual feedback into verbal reflections, store them in episodic memory, and reuse them as context in later trials.

## Evidence

The abstract reports improvements on sequential decision-making, coding, and language reasoning. Consult the paper for setups, baselines, and ablations; this summary does not generalize the results to scientific discovery.

## Reading scope

For AI4S use, evaluate feedback reliability, repeatability, and reflection quality.
