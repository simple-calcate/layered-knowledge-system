# 分层知识体系（Layered Knowledge System）

给 AI 训练 + 给人看的知识库。一个主题 = **一张二维知识平面 + 一个挂载习题池**。

> **注意：`backprop`（反向传播）是示例主题**，只用来验证框架能跑通。
> 框架本身（schema / 标尺 / 质检 / 导出 / 前端画布）与主题内容完全解耦，
> 换主题 = 新建一个 `data/topics/<你的主题>/` 目录，其余什么都不用改。

---

## 一句话架构

```
data/  ← 唯一真相（人来写、人来改）
  ↓  pipeline/validate.py      质检门禁（不过不许进训练）
  ↓  pipeline/export_app.py    → web/data/corpus.json   给前端
  ↓  pipeline/export_training.py → out/training/*.jsonl 给训练
web/   ← 只读 corpus.json，渲染二维画布 + 练习抽屉
```

**两层解耦是核心设计**：

| 层 | 内容 | 措辞要求 | 训练目标 |
|---|---|---|---|
| 第一层：知识平面 | `strict_definition` 严格定义 | **逐字固定**，改一个字都要升 version | 精确记忆 / 零幻觉召回 |
| 第二层：习题池 | 一道题的 N 个解答变体 | **必须换表达，但骨架不变** | 泛化 / 抗过拟合 |

---

## 目录说明

```
schema/axes.backprop.json        两把标尺（X 广度轴 / Y 深度轴）
data/topics/backprop/
  topic.json                     主题元数据 + 写作公约
  nodes.json                     9 个知识点（第一层）
  exercises/*.json               9 道习题 × 3 个等价解答（第二层）
pipeline/
  ksys.py                        数据层公共库：加载 / 骨架闭包 / 跑校验代码
  validate.py                    质检门禁
  garbage_scan.py                乱码注入扫描（中日韩≠西文混排检测）
  repair.py                      JSON 反斜杠转义修复（LaTeX 常见）
  export_app.py                  → 前端 bundle
  export_training.py             → 训练分片
web/                             React 19 + React Flow + Zustand 前端
out/training/                    训练数据产物
```

---

## 常用命令

```bash
npm run validate          # 质检：0 error / 0 warning 才放行
npm run scan:garbage      # 扫乱码注入
npm run sync:app          # 重新生成 web/data/corpus.json
npm run export:training   # 重新生成 out/training/*.jsonl
npm run typecheck         # 前端类型检查
npm run dev               # 起前端（http://localhost:5173）
npm run build             # 类型检查 + 打包
```

改数据请改 `data/`，**不要手改 `web/data/corpus.json` 和 `out/`**，它们是构建产物。

### 推送到 GitHub

正常环境直接 `git push` 即可。若你的网络能连 `api.github.com` 但连不上 `github.com`
（`git push` 报 `Failed to connect to github.com:443`），改用 REST 通道推送：

```bash
python3 tools/push_via_api.py -m "提交说明"
```

它读 `git ls-files` 决定提交范围，走 GitHub Git Data API 建 blob → tree → commit → ref，
效果等同一次 push。前提是先 `gh auth login`。

---

## 当前数据规模（主题 backprop：反向传播与自动微分）

- 9 个知识点，铺在 **5 个概念族（X）× 5 个机制层（Y）** 的平面上
- 9 道习题，27 个解答变体，47 条骨架步骤
- 质检：errors 0 / warnings 0；9/9 道题的 Python 校验代码实际跑通

---

## 三个关键概念（写给第一次上手的人）

**1. 骨架（skeleton）= 判定"两个答案是不是一个意思"的标准**

不是靠人肉判断"这两个说法差不多"，而是给每道题先写一份**有序步骤 DAG**：

```json
"steps": [{"id":"s1","claim":"...","depends_on":[]},
          {"id":"s2","claim":"...","depends_on":["s1"]}],
"terminal_steps": ["s2"]
```

任何一个解答变体，必须覆盖 `s2` 的**传递闭包**（`s2` + 它依赖的 `s1`）。
覆盖了 → 判为等价；漏了 → 打上 `REJECTED_BY_VALIDATOR` 拒绝进训练。
这样"意思相同"就变成了一个**可机器验证**的命题，而不是主观判断。

**2. 可执行校验（checks）= 不信模型自评**

每道题带一段 Python 断言，直接把答案里的数值算一遍。
`validate.py` 会真的 `exec` 这些代码，跑不通就报错。
比如矩阵层那道题，断言 `dW == [[5,5],[7,7],[9,9]]`——硬算出来的，不是让大模型给自己打分。

**3. 坐标是"派生属性"，不是身份**

节点的真实主键是稳定的 `id`；`(x, y)` 只是布局时算出来的展示位置。
所以以后调整轴的划分（比如加一个概念族），只改 `schema/axes.*.json`，
节点本身不动，链接关系也不动。这叫 **graph-first, grid-second**。
