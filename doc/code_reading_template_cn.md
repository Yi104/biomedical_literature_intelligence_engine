# 代码主线阅读模板（中文）

Last updated on: 2026-06-17 (America/Los_Angeles)

## 这份模板是干什么的

这不是系统设计文档。  
这是你在读某条主线代码时，用来防止自己越读越乱的模板。

适用场景：

- 读 `BioRED` relation 主线
- 读 `normalization` 主线
- 读 retrieval / agent 主线
- 以后读别的 NLP 子任务主线

核心目标：

**把“我大概看懂了”变成“我能明确写出输入、输出、关键逻辑和怀疑点”。**

---

## 一、先写这条主线的名字

例子：

- `BioRED relation extraction`
- `rule-based normalization`
- `retrieval -> unified evidence bundle`

模板：

```text
主线名称：
```

---

## 二、这条主线的目标是什么

不要写大话。  
只写这条代码实际在做什么。

例子：

- 把 PubTator 文件解析成 `papers_df / entities_df / relations_df`
- 从 `papers_df + entities_df` 生成 relation candidates 并做分类

模板：

```text
目标：
```

---

## 三、最上层入口函数是什么

先找最上层入口，不要一开始就钻辅助函数。

例子：

- `run_biored_pipeline(...)`
- `predict_biored_relations(...)`

模板：

```text
最上层入口函数：
```

---

## 四、输入是什么

这里一定要区分：

1. **函数参数输入**
2. **真实数据输入**

这两个经常不是一回事。

例子：

- 函数参数有 `query`
- 但真实数据输入其实是 `data_path` 指向的 PubTator 文件

模板：

```text
函数参数输入：

真实数据输入：
```

---

## 五、输出是什么

只写最后稳定输出，不要把中间变量全塞进去。

例子：

- `papers_df`
- `entities_df`
- `relations_df`

模板：

```text
输出：
```

---

## 六、中间关键步骤是什么

这一段只写 3 到 6 步，不要写太细。

例子：

```text
1. 读取 PubTator
2. 解析 entity / relation
3. 生成候选 pair
4. 调 relation classifier
5. 生成 relations_df
```

模板：

```text
关键步骤：
1.
2.
3.
4.
5.
```

---

## 七、candidate 是怎么来的

这个问题在 relation / retrieval / ranking 场景里特别重要。

如果当前主线没有 candidate，也写“无”。

模板：

```text
candidate 来源：
```

---

## 八、label / score / confidence 是怎么来的

这部分专门用来防止你把“看起来有分数”误以为“这个分数很高级”。

你要写清楚：

- label 是模型预测的、规则给的，还是 loader 直接带的
- confidence 是 softmax max、规则分数，还是别的东西

模板：

```text
label 来源：

confidence / score 来源：
```

---

## 九、evidence / provenance 是怎么来的

在你这个项目里，这个问题非常关键。

你要写清楚：

- evidence sentence 是 gold 标注、模型预测，还是 heuristic
- provenance 是 sentence-level、document-level，还是只是一段文本

模板：

```text
evidence 来源：

provenance 来源：
```

---

## 十、这一层和上一层/下一层怎么接

你要写两件事：

1. 它接收谁的输出
2. 它的输出给谁用

模板：

```text
上游输入来自：

下游输出去向：
```

---

## 十一、我目前最不明白的点

这一段非常重要。

不要假装自己都懂了。  
把不明白的地方写出来。

模板：

```text
当前不明白的点：
1.
2.
3.
```

---

## 十二、我最怀疑的错误来源

这里不是让你证明，只是先写 intuition。

例子：

- candidate generation 太粗
- evidence sentence selection 太弱
- normalization 影响 relation pair

模板：

```text
我最怀疑的错误来源：
1.
2.
3.
```

---

## 十三、读完以后我下一步做什么

最后一定要落到动作。

模板：

```text
下一步动作：
```

---

## 附：BioRED relation 主线示例

```text
主线名称：
BioRED relation extraction

目标：
从 BioRED PubTator 数据或其派生实体表中得到 relation evidence rows

最上层入口函数：
run_biored_pipeline(...)

函数参数输入：
query, smoke, data_path, relation_mode, relation_model_path, confidence_threshold

真实数据输入：
BioRED PubTator 文件（data_path）

输出：
papers_df, entities_df, relations_df

关键步骤：
1. load_biored_pubtator_as_dataframes(...)
2. 得到 papers_df / entities_df / gold relations_df
3. 如果 relation_mode=gold，直接返回
4. 如果 relation_mode=model，生成 candidate pairs
5. 调 classifier 预测 relation label 和 confidence
6. 生成 predicted relations_df

candidate 来源：
同一 PMID 内 unique gene x unique disease 的笛卡尔积

label 来源：
gold 模式下来自 PubTator；model 模式下来自 relation classifier

confidence / score 来源：
model 模式下来自 softmax 最大概率；gold 模式下默认 1.0

evidence 来源：
通过 _select_evidence_sentence(...) 从 abstract 中启发式选句

provenance 来源：
后续在 SQLite / retrieval / adapter 层补充 sentence-level provenance 字段

上游输入来自：
BioRED PubTator 文件

下游输出去向：
SQLite -> retrieval -> unified evidence bundle

当前不明白的点：
1. candidate generation 是否过粗
2. evidence sentence heuristic 是否稳定
3. confidence 是否可靠

我最怀疑的错误来源：
1. candidate_generation
2. evidence_sentence
3. confidence

下一步动作：
开始 relation error analysis
```
