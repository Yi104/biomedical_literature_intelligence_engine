# 从哪里开始：Model Quality 工作指南（中文）

Last updated on: 2026-06-16 (America/Los_Angeles)
### what is missing: 
model quality diagnosis stage/ quality optimization stage. 
你已经完成的
• NER/RE 的系统接入
•  unified evidence contract
•  retrieval/agent integration
•  provenance v1
•  evidence bundle 主线
•
文档主线和 repo structure 梳理
你还没完成的
• RE 错误分类
• NER/normalization 错误分类
• relation evidence 质量打磨
• evidence ranking
• 更强的 benchmark/ablation 习惯

### 做 model quality 时

你面对的是：

- 为什么这条 relation 预测错了
- 为什么这个 normalization 没对上
- 为什么 evidence sentence 选错了
- 为什么 confidence 看起来不可信

这些东西的特点是：

- 错误来源很多
- 不容易一眼看出根因
- 你很容易同时怀疑 5 个地方

所以 model quality 工作更像是“诊断系统”。

你现在会 lost，不是因为你不行，而是因为这个阶段本来就更容易失焦。

## 现在你的正确目标是什么

你现在不要再把目标说成：

- 做平台
- 做 biomedical NLP 系统
- 做 knowledge base

这些说法都太大了。

你现在最实际的目标应该是：

**在不再大改架构的前提下，提高 evidence quality。**

更具体一点：

**让最终落到 evidence layer 的 relation / normalization / provenance 更准。**

## 你现在不要做什么

在进入关键部分之前，先停掉这些冲动：

1. 不要继续重构目录
2. 不要继续改 contract 命名
3. 不要继续扩文档框架
4. 不要同时开 3 条 quality line
5. 不要一上来就训新模型

这些事情现在都会让你更乱。

## 你现在真正该从哪里开始

答案很简单：

**先从 BioRED relation extraction 这条主线开始。**

不是因为别的不重要，而是因为：

- 它是你当前 primary task
- 它最贴近最终 evidence value
- 它比 normalization 更直接决定下游 relation evidence 是否成立

## 第一阶段：先建立“主线地图”

这一阶段不要改代码，只做阅读和记笔记。

按这个顺序看：

1. `doc/system_design_v2.md`
2. `doc/data_flow_architecture.md`
3. `doc/unified_evidence_schema.md`
4. `src/extraction/biored_relation_infer.py`
5. `src/extraction/biored_pipeline.py`
6. `tests/unit/test_biored_relation_infer.py`
7. `tests/unit/test_biored_pipeline.py`

### 阅读目标

你要回答下面 6 个问题：

1. 当前 relation 的输入是什么？
2. 当前 relation 的输出是什么？
3. candidate pair 是怎么生成的？
4. relation label 是怎么来的？
5. confidence 是怎么来的？
6. evidence sentence 是怎么选出来的？

如果这 6 个问题你答不清楚，先不要做任何优化。

## 第二阶段：只做 error analysis

这是最重要的一步。

你现在最大的风险不是“模型不够强”，而是：

**你根本还不知道它到底错在哪。**

### 你要做什么

跑一批 BioRED relation inference，然后人工看错误样本。

不是看整体分数，而是看具体错例。

### 你要把错例分成这几类

1. **candidate generation 错**
   - 本来就不该生成这个 pair

2. **relation classification 错**
   - pair 对了，但标签错了

3. **confidence 不可信**
   - 明明很弱，却给了高分
   - 明明很强，却给了低分

4. **evidence sentence selection 错**
   - 关系可能对，但支持句选错了

5. **normalization 影响 relation**
   - entity id 对错直接导致 pair 错

### 为什么这一步最重要

因为后面的改进方向，必须由错误分布决定。

如果你不先做 error analysis，就会变成：

- 怀疑这里
- 改一点
- 再怀疑那里
- 再改一点

最后什么都碰了，但不知道哪个真的有效。

## 第三阶段：只选一条最小改进线

第一轮不要同时优化很多地方。

建议你只在下面三项里选一项：

### 选项 A：candidate generation

适合这种情况：

- 你发现很多假阳性根本来自不合理 pair
- gene/disease 被过度枚举

你可以做的事：

- 限制 pair 生成范围
- 增加句级约束
- 增加 proximity 或简单过滤

### 选项 B：evidence sentence selection

适合这种情况：

- relation 可能对，但 supporting sentence 经常不对
- provenance 看起来弱

你可以做的事：

- 优先选择同时包含 subject/object 的句子
- 优化 `_select_evidence_sentence(...)` 的 tie-break
- 增加更稳定的句子打分规则

### 选项 C：confidence threshold

适合这种情况：

- 预测结果很多，但 precision 明显差

你可以做的事：

- 调高 `confidence_threshold`
- 观察 precision / recall tradeoff

这是最低成本的一种 first pass。

## 为什么我建议你先不要碰 normalization

不是因为 normalization 不重要，而是因为你现在更需要先稳定主任务路径。

如果你一开始就切去做 normalization，你会马上遇到这些问题：

- 是 alias coverage 问题？
- 是 rule 问题？
- 是 label space 问题？
- 是 downstream relation 依赖问题？

它的诊断面会比 relation 更散。

所以建议顺序是：

1. 先把 relation quality 路径摸透
2. 再回头看 normalization
3. 最后再做 evidence ranking

## 你今天就该做什么

如果你今天只做一件事，那就做这个：

### 任务：读 4 个文件并写一页笔记

读：

1. `src/extraction/biored_relation_infer.py`
2. `src/extraction/biored_pipeline.py`
3. `tests/unit/test_biored_relation_infer.py`
4. `tests/unit/test_biored_pipeline.py`

写笔记时固定回答：

- 输入是什么
- 输出是什么
- candidate 怎么来
- confidence 怎么来
- evidence sentence 怎么来
- 你最怀疑哪一块最容易出错

只要你把这页笔记写出来，你就会比现在清楚很多。

## 如果你明天继续做什么

明天就做：

### 任务：开始错误分析

目标不是“提高分数”，而是建立一个错例分类表。

建议你做一个简单表格，字段如下：

- `pmid`
- `entity1`
- `entity2`
- `predicted_relation`
- `gold_relation`（如果有）
- `confidence`
- `evidence_sentence`
- `error_type`
- `notes`

其中 `error_type` 只能从下面选：

- `candidate_generation`
- `classification`
- `confidence`
- `evidence_sentence`
- `normalization`
- `other`

这张表会成为你后面所有优化的依据。

## 一周内最合理的节奏

### Day 1

- 读主线 relation 文件
- 写一页结构笔记

### Day 2

- 跑 relation inference
- 收集样本

### Day 3

- 做错误分类
- 看哪一类最多

### Day 4-5

- 只修一个问题
- 不要同时改两条线

### Day 6-7

- 重新观察结果
- 决定下一轮是继续 relation 还是转 normalization

## 你现在最需要记住的三句话

1. **先分析，再优化。**
2. **一次只打一条质量线。**
3. **先修最靠近主任务的错误。**

## 最后一句最实用的话

如果你现在完全不知道从哪开始，就不要问“整个项目该怎么做”，只问：

**“BioRED relation 这一条，今天我能读明白哪 4 个文件？”**

这就是正确起点。

