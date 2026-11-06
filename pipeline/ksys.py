"""ksys.py — 概念知识网的数据层公共入口。

模型（v3）：
    concept（一个名词）
      └── question（二维问题网上的一格，坐标 x/y 只是布局）
            └── canonical（这道题唯一被认定为正确的答案：要点清单 + 审核信息）
                  └── answer（同一意思的不同表达，必须覆盖全部要点）

目录结构刻意做成「一个文件一张卡片」：
    多人同时贡献时各加各的文件，不会挤在同一个 JSON 里产生合并冲突。

设计约定：
  - 每道题只有一个正确答案（canon），由维护者审核认定，改动 canon 须走审核
  - 同一题下的多条答案只是「换说法」，意思必须与 canon 完全一致
  - 不收录互相矛盾的对立主张；有异议走 PR 修订 canon，而不是并列第二种
  - 只有 canon 及其同义改写会进入训练数据；未采纳的说法不放在 data/ 下
  - 坐标是派生属性，卡片 id 才是稳定主键
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "concepts"
SCHEMA_FILE = ROOT / "schema" / "axes.json"

# --------------------------------------------------------------------------
# 乱码/注入检测：正常中文书写里西文与汉字之间必定有空格，
# 所以「汉字与西文直接相邻」是极强的乱码信号。
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
    return INLINE_CODE.sub(" ", CODE_FENCE.sub(" ", text))


def find_garbage(text: str) -> list[str]:
    t = clean_for_scan(text)
    hits = set(ADJACENT.findall(t)) | set(CYRILLIC.findall(t))
    return sorted(h for h in hits if len(h.strip()) > 3)


def iter_strings(obj, path: str = "$"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")


def content_hash(text: str) -> str:
    norm = re.sub(r"\s+", " ", text.strip())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_folder(folder: Path) -> list[tuple[Path, dict]]:
    if not folder.is_dir():
        return []
    return [(p, _read(p)) for p in sorted(folder.glob("*.json"))]


class Concept:
    def __init__(self, concept_id: str, folder: Path):
        self.id = concept_id
        self.dir = folder
        self.meta = _read(folder / "concept.json")
        self.question_files = _load_folder(folder / "questions")
        self.canonical_files = _load_folder(folder / "canonical")
        self.answer_files = _load_folder(folder / "answers")
        self.questions = [d for _, d in self.question_files]
        self.canonicals = [d for _, d in self.canonical_files]
        self.answers = [d for _, d in self.answer_files]

    @property
    def questions_by_id(self) -> dict[str, dict]:
        return {q["id"]: q for q in self.questions}

    @property
    def canonicals_by_id(self) -> dict[str, dict]:
        return {s["id"]: s for s in self.canonicals}

    def canonicals_of(self, question_id: str) -> list[dict]:
        return [s for s in self.canonicals if s["question_id"] == question_id]

    def answers_of(self, question_id: str) -> list[dict]:
        return [a for a in self.answers if a["question_id"] == question_id]


class Corpus:
    """一次加载全部概念与两把标尺。校验器与导出器共用这一个入口。"""

    def __init__(self):
        self.axes = _read(SCHEMA_FILE)
        self.concepts: list[Concept] = []
        for folder in sorted(DATA_DIR.iterdir()):
            if folder.is_dir() and (folder / "concept.json").exists():
                self.concepts.append(Concept(folder.name, folder))

    @property
    def x_levels(self) -> dict[int, dict]:
        return {lv["x"]: lv for lv in self.axes["x_axis"]["levels"]}

    @property
    def y_levels(self) -> dict[int, dict]:
        return {lv["y"]: lv for lv in self.axes["y_axis"]["levels"]}

    def views(self):
        """组装成前端/导出器要用的视图：question → canonical → answers。

        每条 answer 附带 misses（漏掉的要点 id），供质检与训练过滤使用。
        canonical 为 None 表示这道题还没人认定正确答案。
        """
        for c in self.concepts:
            for q in c.questions:
                cans = c.canonicals_of(q["id"])
                canon = cans[0] if cans else None
                inv_ids = [i["id"] for i in canon.get("invariants", [])] if canon else []
                answers = [
                    {**a, "misses": sorted(set(inv_ids) - set(a.get("covers", [])))}
                    for a in c.answers_of(q["id"])
                ]
                yield c, q, canon, answers
