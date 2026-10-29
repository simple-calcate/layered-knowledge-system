"""ksys.py — 双层知识体系的数据层公共入口。

加载 data/topics/<topic>/ 下的 topic.json / nodes.json / exercises/*.json，
并提供一批被 validate.py 与 export 脚本共用的校验原语。

设计约定：
  - 节点的真实身份是稳定 id；二维坐标只是布局属性
  - 一道习题可容多个解答；「等价」的判据是共享同一份 answer_skeleton
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "topics"


def content_hash(text: str) -> str:
    """对一段文本取稳定短摘要。

    用途：给「定义」这类必须逐字复现的内容打指纹。
    训练侧拿它做回归门禁——同一 term 的定义一旦被改动，指纹就变，
    从而能立刻发现模型召回的是旧版本还是新版本。
    """
    norm = re.sub(r"\s+", " ", text.strip())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# 注入/乱码检测
# 正常中文书写里，西文单词与汉字之间必定有空格。
# 因此「汉字与西文直接相邻」是一个极强的乱码信号。
# --------------------------------------------------------------------------

CJK = r"\u4e00-\u9fff"
OTHER_LETTER = r"\u0100-\u024f\u0370-\u03ff\u0400-\u04ff"
ADJACENT = re.compile(
    rf"([{CJK}][A-Za-z{OTHER_LETTER}]{{3,}}|[{OTHER_LETTER}A-Za-z]{{3,}}[{CJK}])"
)
CYRILLIC = re.compile(r"[\u0400-\u04ff]{3,}")
CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def clean_for_scan(text: str) -> str:
    """去掉围栏代码块与行内代码，剩下的才是要扫的自然语言。"""
    return INLINE_CODE.sub(" ", CODE_FENCE.sub(" ", text))


def find_garbage(text: str) -> list[str]:
    t = clean_for_scan(text)
    hits = set(ADJACENT.findall(t)) | set(CYRILLIC.findall(t))
    return sorted(h for h in hits if len(h.strip()) > 3)


def iter_strings(obj, path: str = "$"):
    """递归产出 (路径, 字符串)。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


# --------------------------------------------------------------------------
# 主题加载
# --------------------------------------------------------------------------


class Topic:
    def __init__(self, topic_id: str):
        self.topic_id = topic_id
        self.dir = DATA_DIR / topic_id
        if not self.dir.is_dir():
            raise FileNotFoundError(f"未找到主题目录: {self.dir}")

        self.meta: dict = self._read(self.dir / "topic.json")

        axes_rel = self.meta.get("axes_file")
        axes_path = (ROOT / axes_rel) if axes_rel else (self.dir / "axes.json")
        self.axes: dict = self._read(axes_path)

        nodes_doc = self._read(self.dir / "nodes.json")
        self.nodes: list[dict] = nodes_doc.get("nodes", []) if isinstance(nodes_doc, dict) else nodes_doc

        self.exercises: list[dict] = []
        ex_dir = self.dir / "exercises"
        if ex_dir.is_dir():
            for fp in sorted(ex_dir.glob("*.json")):
                doc = self._read(fp)
                if isinstance(doc, list):
                    self.exercises.extend(doc)
                else:
                    self.exercises.append(doc)

        self._nodes_by_id = {n.get("id"): n for n in self.nodes}
        self._exercises_by_id = {e.get("id"): e for e in self.exercises}

    @staticmethod
    def _read(path: Path) -> dict:
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    # -- 索引 --
    @property
    def nodes_by_id(self) -> dict:
        return self._nodes_by_id

    @property
    def exercises_by_id(self) -> dict:
        return self._exercises_by_id

    @property
    def families(self) -> dict[str, dict]:
        return {f["key"]: f for f in self.axes["x_axis"]["families"]}

    @property
    def strata(self) -> dict[int, dict]:
        return {lv["value"]: lv for lv in self.axes["y_axis"]["levels"]}

    @property
    def x_of_family(self) -> dict[str, int]:
        return {f["key"]: f["x"] for f in self.axes["x_axis"]["families"]}

    def canvas(self, node: dict) -> tuple[int, int]:
        return self.x_of_family[node["family_key"]], node["stratum"]


# --------------------------------------------------------------------------
# 解题骨架相关的校验原语
# --------------------------------------------------------------------------


def step_index(skeleton: dict) -> dict[str, dict]:
    return {s["id"]: s for s in skeleton.get("steps", [])}


def terminal_closure(skeleton: dict) -> set[str]:
    """终局步骤及其依赖闭包。用于「每个解答都必须覆盖」的判据。"""
    idx = step_index(skeleton)
    seeds = skeleton.get("terminal_steps") or [s["id"] for s in skeleton.get("steps", [])]
    seen: set[str] = set()
    stack = list(seeds)
    while stack:
        cur = stack.pop()
        if cur in seen or cur not in idx:
            continue
        seen.add(cur)
        stack.extend(idx[cur].get("depends_on", []))
    return seen


def has_cycle(skeleton: dict) -> list[str]:
    """检测 skeleton 内部的环，返回环上的节点（空列表表示无环）。"""
    idx = step_index(skeleton)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in idx}
    stack_path: list[str] = []

    def dfs(u: str) -> list[str]:
        color[u] = GRAY
        stack_path.append(u)
        for v in idx[u].get("depends_on", []):
            if v not in idx:
                continue
            if color[v] == GRAY:
                return stack_path[stack_path.index(v):] + [v]
            if color[v] == WHITE:
                got = dfs(v)
                if got:
                    return got
        stack_path.pop()
        color[u] = BLACK
        return []

    for k in idx:
        if color[k] == WHITE:
            got = dfs(k)
            if got:
                return got
    return []


def topo_order(skeleton: dict) -> list[str]:
    """骨架步骤的拓扑序（被依赖的在前）。有环时返回空列表。"""
    if has_cycle(skeleton):
        return []
    idx = step_index(skeleton)
    out: list[str] = []
    seen: set[str] = set()

    def visit(u: str) -> None:
        if u in seen:
            return
        seen.add(u)
        for v in idx[u].get("depends_on", []):
            if v in idx:
                visit(v)
        out.append(u)

    for k in idx:
        visit(k)
    return out


# --------------------------------------------------------------------------
# 可执行校验（形式化不变量里能用程序判的那部分，绝不让 LLM 自评）
# --------------------------------------------------------------------------


def run_checks(exercise: dict) -> tuple[bool, str]:
    """执行 exercise.checks 里所有 kind == python 的断言，返回 (是否通过, 说明)。"""
    for chk in exercise.get("checks", []):
        if chk.get("kind") != "python":
            continue
        ns: dict = {}
        try:
            exec(compile(chk["code"], f"<check:{exercise.get('id')}>", "exec"), ns)  # noqa: S102
        except Exception as exc:  # noqa: BLE001
            return False, f"{chk.get('name', 'unnamed')}: {type(exc).__name__}: {exc}"
    return True, "ok"
