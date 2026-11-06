# 概念知识网（layered-knowledge-system）

给 AI 训练、也给人看的知识库。**原点是一个名词，不是一段定义。**

围绕「知识」这样的概念，向两个方向铺开一张问题网：

- **X 轴 · 问题类型**：是什么 / 为什么 / 如何获取 / 如何区分
- **Y 轴 · 追问层次**：基本界定 / 边界辨析 / 跨界追问

每道题有**一个经审核认定的真实正确答案**，写成一份要点清单；
这个正确答案可以有**很多条同义改写**（意思必须不变，表达可以完全不同）。
AI 只学这一组，不接触互相矛盾的说法。

> 演进记录：`backprop` 严格定义模型（10-30）→ 多立场并列 v2（11-04）→ 单一正确立场 v3（11-06）。
> 仓库里唯一的示例概念是「知识」，用来验证框架能跑通，不代表这些答案本身是哲学定论。
> v2 中与正确答案冲突的卡片保留在 `archive/unadopted/`，不参与构建与训练。

---

## 为什么这样设计

| | 早期做法（已废弃） | v2（已废弃） | 现在 v3 |
|---|---|---|---|
| 原点 | 知识点的固定定义 | 一个名词 | 一个名词 |
| 二维格子 | 概念族 × 机制层 | 问题类型 × 追问层次 | 不变 |
| 多个答案 | 只准同义改写 | 先分**立场**，立场间可矛盾 | **只有一个正确意思**，其余全是它的改写 |
| 等价判定 | 骨架 DAG 闭包 | 立场下的不变量清单 | 正确要点清单，`covers` 必须全覆盖 |
| 训练数据 | 记忆 + 泛化 | 按立场隔离 chosen_group | 只有一个 chosen 组，冲突说法不导出 |

关键的一点：**训练数据里不能出现互相矛盾的答案**。
所以 canonical 是唯一真值来源，由维护者审核认定；有异议走 PR 修订它，
而不是并列第二份。这样模型学到的是「一个确定意思的多种措辞」，
既不会把矛盾当等价，也不会因为只背一句话而过拟合。

「意思有没有变」不靠感觉：每份 canon 写几条**正确要点**，
该题下每条改写都要逐条覆盖，漏一条质检直接报错。

---

## 目录

```
schema/axes.json                    两把标尺（X 四列 / Y 三层），对所有概念通用
data/concepts/knowledge/
  concept.json                     概念原点：名词、别名、简介、作者
  questions/q.*.json               一题一文件
  canonical/c.*.json               一题一份正确答案（要点 + 依据 + 审核），改动须审核
  answers/a.*.json                 一说法一文件，含署名与出处
archive/unadopted/                 旧版冲突卡片，只留档，不参与任何构建
pipeline/
  ksys.py                          加载器 + 乱码检测
  validate.py                      质检门禁（本地与 CI 同一份）
  export_app.py                    → web/data/corpus.json
  export_training.py               → out/training/*.jsonl
  garbage_scan.py / repair.py      辅助工具
tools/
  new_card.py                      交互式生成一张贡献卡片
  push_via_api.py                  github.com 不通时改走 REST；受保护分支自动走 PR
web/                               React 19 + React Flow 画布 + 答案抽屉
.github/CODEOWNERS                 保护 canonical/，改动须 code owner 批准（已硬性生效）
.github/workflows/validate.yml     PR 自动质检
CONTRIBUTING.md                   贡献者指南
```

**一个文件一张卡片**是整个共享生态的关键：多个人同时贡献时各加各的文件，
Git 不会冲突。`canonical/` 是唯一例外——一题只有一份，所以走审核门禁。

---

## 常用命令

```bash
npm run validate          # 质检：署名、坐标、要点覆盖、审核状态、重复、乱码
npm run new:card          # 交互式生成一张卡片（推荐给贡献者）
npm run scan:garbage      # 单独扫乱码
npm run sync:app          # 重建 web/data/corpus.json
npm run export:training   # 重建 out/training/*.jsonl
npm run typecheck         # 前端类型检查
npm run build             # 类型检查 + 打包到 web/dist
npm run dev               # 开发服务器
```

改数据请改 `data/`，**不要手改 `web/data/corpus.json` 与 `out/`**，它们是构建产物。

---

## 训练数据怎么分流

| 文件 | 内容 | 用途 |
|---|---|---|
| `recall.jsonl` | 概念→问题清单、坐标→问题、轴枚举、**问题→正确要点** | 结构与真值记忆，低温度 SFT |
| `generalize_sft.jsonl` | 一条合格改写一行，带风格/署名/要点 id | 一题多答的普通 SFT |
| `generalize_group.jsonl` | 每题**一个** `chosen` 组 | GRPO / DPO / KTO 组内偏好 |
| `invariant_probe.jsonl` | 由答案还原正确要点 | 评测是否守住真值，不参与训练 |

**未采纳的说法不进入任何分片**：冲突内容放在 `archive/unadopted/`，不在加载范围内；
漏掉要点的改写被直接丢弃，连标记都不留在训练文件里。
`manifest.json` 里 `guard.excluded_unadopted` 记录这条策略。

---

## 共享生态

新人想加东西，只需要：

```bash
python3 tools/new_card.py      # 按提示填，自动生成一个 JSON，covers 也帮填好
python3 pipeline/validate.py   # 自检
```

然后开 PR。CI 跑同一份质检：

- `main` 已开分支保护，**所有改动都必须走 PR**，没有人能直接 push 到 main
- 只加 `answers/` / `questions/` 的 PR 不要求批准，CI 过了就能合并
- 动 `canonical/` 的 PR 被 **Require review from Code Owners** 硬性阻断，
  必须 `@simple-calcate` 批准才能合并；CI 也会提示

合并后由维护者重新生成画布与训练分片。完整说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 推送到 GitHub

`main` 受分支保护，正常环境下应当 **建分支 → 开 PR → 合并**。
若网络能连 `api.github.com` 但连不上 `github.com`（`git push` 报
`Failed to connect to github.com:443`），改用 REST 通道，它会自动走同样的 PR 流程：

```bash
python3 tools/push_via_api.py -m "提交说明"
python3 tools/push_via_api.py -m "应急直推" --direct   # 跳过 PR，仅在紧急时用
```

工具内部：

1. 从远端 `main` 的 HEAD 取 **parent**，用 `git ls-files` 的文件一次性建树，
   再建 commit（历史是累积的，不会覆盖旧提交）
2. 探测 `main` 是否受保护：受保护就建临时分支 → 开 PR → 合并 → 删除临时分支；
   未受保护则快进更新 `main`
3. 认证用 `gh auth token`，前提是先 `gh auth login`

一个刻意的取舍：保护规则里 `Include administrators` 是**关**的。
也就是说 **CODEOWNERS 硬性挡住的是外部贡献者**，仓库主人仍可自助合并自己的 PR——
否则连日常同步都要主人给自己点一次 Approve，工作流会被卡死。
想连主人一起锁死，去仓库设置里勾上它即可，但那样每次同步都得人工批准。
