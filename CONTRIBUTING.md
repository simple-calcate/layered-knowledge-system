# 给知识库添砖加瓦

欢迎。本库的原则很简单：**一道题只有一个真实正确的答案**，AI 只学这一个；
但同一个意思可以有**很多种说法**——这些说法用来教模型别被措辞困住，而不是教它几种互相矛盾的主张。

## 先理解四个词

| 词 | 意思 | 举例 |
|---|---|---|
| 概念 concept | 一个名词，是整张网的原点 | 知识 |
| 问题 question | 二维问题网上的一格，有坐标 | X1Y1「知识是什么？」 |
| 正确答案 canonical | 这道题经审核认定的唯一正确意思，写成一份要点清单 | 3 条要点 + 认定依据 |
| 同义改写 answer | 同一正确意思的另一种表达 | 平实叙述 / 比喻 / 分点说明 |

判定「意思变没变」不靠感觉：每份 canon 先写几条**要点（不变量）**，
该题下每条答案都要 `covers` 覆盖全部要点，`validate.py` 会自动检查，漏一条就报错。

## 最快的一条路：补一条说法

```bash
python3 tools/new_card.py answer
```

按提示选问题、写正文，工具会自动把 `covers` 填好（`canonical_id` 也帮你带上）。

```bash
python3 pipeline/validate.py     # 自检，看到「质检通过」再提交
```

**只加 `answers/` 文件的 PR 最轻**，不需要动任何人的东西，CI 过了就能合并。

## 想改「正确答案」怎么办

**不要新建第二份 canon 来和它并存。** 一题只允许一份，质检会直接拦下。
如果你认为现有的正确答案写错了、或者有更准确的依据：

1. 在 PR 里写清依据：出处、推理、反例，哪一条要点该改
2. 修改对应的 `canonical/c.<问题>.json`，同时更新 `basis`（认定依据）和 `review`（审核人）
3. `main` 已开分支保护，`CODEOWNERS` 会**硬性阻断**这个 PR，
   直到 `@simple-calcate` 点 Approve 才能合并（不是"自动请求审阅"那种软提醒）
4. 合并后由维护者重新生成画布与训练分片

这条审核门禁是刻意的：**训练数据里出现一条错的，AI 就会学到一条错的。**
`new_card.py canonical` 生成的卡片默认是 `pending`，质检会拦下，就是在提醒这一步还没走完。

## 加一道新问题

```bash
python3 tools/new_card.py question
```

选 X 列（问题类型）和 Y 层（追问层次）即可。**一格只放一个问题**。
新问题默认没有正确答案，属于「待补格」，等有人提交 canon。

## 加一个新概念

复制 `data/concepts/knowledge/` 整个目录，改名成你的概念（英文小写），
把 `concept.json` 里的 `id`、`term`、`aliases`、`summary`、`author` 换掉，
再清空 `questions/`、`canonical/`、`answers/` 里的示例文件，从第一张卡片开始。

## 目录为什么这么设计

```
data/concepts/knowledge/
  concept.json              概念本身
  questions/q.*.json        一题一文件
  canonical/c.*.json        一题一份正确答案，改动须审核
  answers/a.*.json          一说法一文件，随便加
archive/unadopted/          旧版被判定与正确答案冲突的内容，只留档
```

**一个文件一张卡片 = 多个人同时贡献时各加各的文件，Git 不会冲突。**
如果所有内容挤在一个大 JSON 里，两个 PR 几乎必然要手工解冲突。
`canonical/` 是唯一例外：它一题只有一份，所以不能各写各的，必须走审核。

`archive/unadopted/` 里的文件**不在 `data/concepts/` 下**，因此质检、前端打包、
训练导出都读不到，AI 训练数据里不会包含它们。要留存不同主张请放这里，别放回 `data/`。

## 提交流程

1. `python3 tools/new_card.py` 生成卡片，写内容
2. `python3 pipeline/validate.py` 本地自检
3. 建分支、提交、开 PR（`main` 受保护，不能直接 push）
4. CI 跑同一份质检：
   - 只动 `questions/` / `answers/` 的 PR **不要求批准**，CI 过了就能合并
   - 动了 `canonical/` 的 PR 必须等 code owner 批准，系统会挡住合并按钮
5. 合并后画布与训练分片由维护者重新生成

> 为什么"只加一条说法"也要走 PR：GitHub 的分支保护是**整条分支**的规则，
> 没法只对某个目录放开。所以用「批准数 = 0 + 要求 code owner 审阅」这个组合，
> 把强制审核精确落在 `canonical/` 上，其余 PR 只是走个流程、不需要等人。

## 写卡片的几条规矩

- **署名和出处必填**。原创就写「原创」，转述别人的观点要注明来自哪本书、哪一派。
- **同义改写不是复制粘贴**。换的是表达和切入角度，正确要点一条都不能少；逐字相同会被质检拦下。
- **不要引入第二种主张**。有异议走 PR 修订 canon，不要并列第二份答案要点。
- **空格不用填**。矩阵里的空缺代表「还没人问过」，不需要为凑满而编问题。
- **别手改 `web/data/corpus.json`**，它是构建产物。

## 数据字典（懒得用工具、想手写时看这里）

```
question  : schema, id, concept_id, x, y, text, note, author{name,link}, created_at
canonical : schema, id, question_id, label, invariants[{id,claim}], basis,
            author, review{status,by,at,policy}, created_at, status
answer    : schema, id, concept_id, question_id, canonical_id, style, register,
            content, covers[], author, source{type,note}, created_at, status
```
