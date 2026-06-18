# 如何以这个平台为例，自学 Biomedical NLP / IE

Last updated on: 2026-06-16 (America/Los_Angeles)

## 这份文档要解决什么问题

如果你现在的困惑是：

- 我知道这个项目能跑起来
- 但我不知道“接下来怎么学”
- 我不知道文献应该怎么配合代码一起看
- 我不知道 error analysis、baseline、benchmark、ablation 这些到底怎么落地

这份文档就是给你一个**学习框架和行动逻辑**。

它不是论文，也不是教程全集。  
它的作用是：

**让你知道自己现在处于哪一阶段，下一步该学什么，为什么要这么学。**

---

## 1. 先搞清楚：你现在到底在学什么

你现在不是单纯在学：

- Python 工程
- 一个模型怎么调用
- 一个 benchmark 怎么跑分

你其实是在同时学 4 件事：

1. **系统层**
   - biomedical evidence platform 怎么搭
   - extraction / normalization / retrieval / evidence bundle 怎么连起来

2. **任务层**
   - NER、normalization、relation extraction、provenance 分别解决什么问题

3. **实验层**
   - baseline 怎么定义
   - benchmark 怎么跑
   - ablation 怎么做
   - error analysis 怎么做

4. **研究层**
   - 为什么这个方法有效
   - 为什么这个错误会发生
   - 下一步优化应该打哪里

所以你现在会觉得乱，是因为你其实不是只在学一件事。

---

## 2. 用这个平台自学，最合理的阶段划分

我建议你把整个自学过程分成 5 个阶段。

## 阶段 A：读懂系统，不急着改模型

### 目标

先知道这个平台是怎么流动的。

### 你应该读什么

先看：

1. `doc/system_design_v2.md`
2. `doc/data_flow_architecture.md`
3. `doc/unified_evidence_schema.md`
4. `README.md`

然后看代码目录：

1. `src/contracts/`
2. `src/kb/`
3. `src/retrieval/`
4. `src/agent/`
5. `src/extraction/`

### 这一阶段你要回答的问题

1. 文献文本怎么进系统？
2. entity / relation 怎么表示？
3. evidence 最后长什么样？
4. retrieval 和 agent 各自负责什么？
5. 现在平台真正的主任务是什么？

### 阶段 A 的输出

你应该能自己说清楚这句话：

> 这个项目现在的主线，是把 biomedical literature 变成可检索、可追溯、可被下游消费的 evidence objects。

如果这句话你还说不顺，就先别往模型质量走。

---

## 阶段 B：读懂主任务，不急着提分

你现在的主任务不是所有东西一起学，而是：

**先读懂 BioRED relation extraction 这条主线。**

### 为什么先选这条

因为：

- 这是当前 primary task
- 它最接近 evidence layer 的核心价值
- 它最适合训练你做 error analysis

### 这一阶段重点看什么

1. `src/extraction/biored_pipeline.py`
2. `src/extraction/biored_loader.py`
3. `src/extraction/biored_relation_infer.py`
4. `tests/unit/test_biored_pipeline.py`
5. `tests/unit/test_biored_relation_infer.py`

### 这一阶段你要回答的问题

1. 输入是什么？
2. 输出是什么？
3. candidate pair 怎么生成？
4. relation label 怎么预测？
5. confidence 怎么来？
6. evidence sentence 怎么来？

### 阶段 B 的输出

你应该能画出这条局部流程：

```text
papers_df + entities_df
  -> candidate generation
  -> relation classification
  -> relations_df
  -> SQLite
  -> retrieval
  -> unified evidence bundle
```

---

## 阶段 C：学会 error analysis

这一步是你真正从“会跑代码”进入“会做 NLP 项目”的分界线。

### 先记住一句话

**不要一上来就优化模型，先看它到底错在哪。**

### 你为什么必须学 error analysis

因为在这个项目里，一个坏结果可能来自：

- NER span 错
- entity type 错
- normalization 错
- candidate generation 错
- relation classification 错
- evidence sentence selection 错
- confidence 不可信

如果你不拆错因，就会永远乱改。

### 推荐的错误分类框架

你可以先用下面这些类：

1. `candidate_generation`
2. `classification`
3. `confidence`
4. `evidence_sentence`
5. `normalization`
6. `other`

### 推荐你记录的字段

做一个简单表格，至少有：

- `pmid`
- `entity1_text`
- `entity2_text`
- `entity1_id`
- `entity2_id`
- `predicted_relation`
- `gold_relation`
- `confidence`
- `evidence_sentence`
- `error_type`
- `notes`

### 这一阶段的输出

你应该得到一个错误分布判断，例如：

- 40% 是 candidate 太粗
- 30% 是 relation label 错
- 20% 是 evidence sentence 选得差
- 10% 是 normalization 导致 pair 错

只要有这个分布图，你后面才知道优先修哪里。

---

## 阶段 D：学会“如何提高模型质量”

这里的重点不是“疯狂换模型”，而是学会按层优化。

## 4.1 先选一条质量线，不要同时做三条

这个项目里主要有三条质量线：

1. relation extraction quality
2. normalization quality
3. evidence ranking quality

建议顺序：

1. **relation extraction**
2. **normalization**
3. **evidence ranking**

原因：

- relation 是当前主任务
- normalization 会影响 relation，但一开始更容易散
- ranking 建立在前面两层基本可用的前提上

## 4.2 提高关系抽取质量时，常见可改点

### A. candidate generation

看这些问题：

- pair 枚举是不是太多？
- 是否应该加句级约束？
- 是否应该加类型、距离、共现过滤？

### B. relation classification

看这些问题：

- label confusion 主要发生在哪些类？
- `No_Relation` 和正类之间怎么错？
- 某些 relation type 是否样本太少？

### C. evidence sentence selection

看这些问题：

- supporting sentence 是否真的 support 这个 relation？
- 现在选句规则是不是太弱？

### D. confidence threshold

看这些问题：

- precision/recall tradeoff 是不是合理？
- 高 confidence 错例多不多？

## 4.3 提高 normalization 质量时，常见可改点

### A. coverage

- 高频 mention 有没有没被 normalize？
- unresolved 的比例是多少？

### B. ambiguity

- 同一个 alias 会不会对应多个 ID？
- 当前规则是不是过于贪心？

### C. entity typing interaction

- 是 normalization 本身错了
- 还是 upstream entity type 本来就错了

## 4.4 提高 evidence ranking 质量时，常见可改点

前提是 relation 和 normalization 已经比较稳定。

你可以开始定义：

- 什么叫 support 更强？
- 什么叫 evidence 更相关？
- 置信度和 evidence quality 是不是应该分开？

---

## 5. 常规实验 workflow 应该怎么学

这是你问的重点：baseline、benchmark、ablation 到底是什么逻辑。

## 5.1 Baseline

### baseline 是什么

baseline 不是“最差模型”，而是：

**一个可重复、可比较、以后所有改动都拿它作参照的起点。**

### 在这个项目里，baseline 应该是什么

例如：

- 当前 BioRED relation inference 配置
- 当前 confidence threshold
- 当前 candidate generation 逻辑
- 当前 normalization 规则版本

### 你学 baseline 时要学什么

不是只看分数，而是看：

- baseline 输入是什么
- baseline 输出是什么
- baseline 有哪些已知缺陷
- baseline 的主要错误分布是什么

---

## 5.2 Benchmark

### benchmark 是什么

benchmark 是：

**你用来评价一个方法好不好的一套固定任务和指标。**

### 你要学的不是“跑 benchmark”

而是：

- 这个 benchmark 测到了什么
- 没测到什么
- 它和你的 downstream 目标一致吗

### 在你这个项目里要有两个 benchmark 视角

1. **task benchmark**
   - 例如 relation classification 的 F1

2. **downstream usefulness benchmark**
   - evidence 是否更可信
   - entity pair 是否更准
   - retrieved support 是否更有用

这第二类在很多论文里不一定完整给你，但对你这个项目很重要。

---

## 5.3 Ablation

### ablation 是什么

ablation 不是随便关一点东西看看。

它的本质是：

**为了知道“到底是哪一个因素在起作用”，而做的控制实验。**

### 你应该怎么学 ablation

先建立规则：

1. 一次只改一个主要因素
2. 改动前后用同一套评价
3. 记录 precision、recall、F1，不只看一个数
4. 同时看错例分布有没有变化

### 在你这个项目里，典型 ablation 例子

例如：

- 有无 candidate filtering
- 不同 confidence threshold
- 不同 evidence sentence selection 规则
- 不同 normalization 规则版本

### 一个典型错误做法

不要这样：

- 同时换模型
- 同时改阈值
- 同时改 candidate generation
- 然后说“结果更好了”

这种实验学不到东西。

---

## 6. 你什么时候该看文献

你提到“有一些方法确实需要参考文献”，这个判断是对的。

但不要一开始就无差别读很多论文。

### 最有效的顺序

#### 第一步：先知道自己卡在哪

例如你发现：

- candidate 太粗
- evidence sentence selection 很弱
- relation label 常混淆

#### 第二步：再按问题去找文献

例如：

- entity-aware relation extraction
- biomedical relation classification
- sentence selection / evidence retrieval
- normalization / entity linking

### 这样读文献才不会漂

否则你会很容易出现：

- 论文看了很多
- 但不知道和当前问题怎么接

你现在最需要的是：

**问题驱动的阅读，不是主题驱动的阅读。**

---

## 7. 一个最推荐的自学节奏

## 第一周

目标：读懂主线 + 开始错误分析

做：

1. 读 relation 主线文件
2. 写一页流程笔记
3. 跑一批 relation inference
4. 开始收集错例

## 第二周

目标：完成第一轮 error analysis

做：

1. 给错例分类
2. 找出最大头的问题
3. 只选一个点做第一轮优化

## 第三周

目标：学 baseline / ablation 的最小实践

做：

1. 固定 baseline
2. 做一个单因素改动
3. 记录前后变化
4. 看错例分布有没有改善

## 第四周

目标：开始把经验固化

做：

1. 把有效规则写回代码
2. 把实验流程写成笔记
3. 补稳定的 evaluation 记录方式

---

## 8. 如果你现在完全懵，今天只做什么

今天只做这件事：

### 打开并读完这 4 个文件

1. `src/extraction/biored_relation_infer.py`
2. `src/extraction/biored_pipeline.py`
3. `tests/unit/test_biored_relation_infer.py`
4. `tests/unit/test_biored_pipeline.py`

然后写一页纸回答：

- 输入是什么
- 输出是什么
- candidate 怎么生成
- confidence 怎么来
- evidence sentence 怎么来
- 哪一块最可能有问题

这一步就是你真正的 start。

---

## 9. 最后一句话

你现在不是在“重新发明成熟平台”，也不是在“空想一个大系统”。

你是在用这个平台做一个非常重要的训练：

**学习如何把成熟方法、系统集成、错误分析、实验设计和质量提升连成一个完整过程。**

这就是这个项目对你最有价值的地方。
