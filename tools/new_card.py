#!/usr/bin/env python3
"""new_card.py — 交互式生成一张贡献卡片，不用手写 JSON、不用记字段。

用法：
    python3 tools/new_card.py            # 会问你要加什么
    python3 tools/new_card.py answer     # 直接加一条同义改写（最常见）

为什么一个文件一张卡片：
    两个人同时贡献时，各写一个新文件，Git 不会冲突、也不用商量谁先合并。
    例外是 canonical/：一题一份，改动须 code owner 审核（见 CODEOWNERS）。

生成的卡片只是起点，内容请自己改；写完跑 python3 pipeline/validate.py 自检。
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from ksys import Corpus  # noqa: E402

DATA = ROOT / "data" / "concepts"


def ask(prompt: str, default: str = "") -> str:
    tip = f"（默认 {default}）" if default else ""
    v = input(f"{prompt}{tip}: ").strip()
    return v or default


def pick_from(label: str, options: list[tuple[str, str]]) -> str:
    print(f"\n{label}:")
    for i, (key, desc) in enumerate(options, 1):
        print(f"  {i}. {key}  {desc}")
    while True:
        v = ask("输入序号或键值")
        if v.isdigit() and 1 <= int(v) <= len(options):
            return options[int(v) - 1][0]
        if v in [k for k, _ in options]:
            return v
        print("  没认出来，再来一次。")


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "card"


def write_card(folder: Path, filename: str, payload: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{filename}.json"
    if p.exists():
        print(f"文件已存在，拒绝覆盖：{p}")
        sys.exit(1)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def author_block() -> dict:
    return {"name": ask("你的署名"), "link": ask("主页链接（可留空）", "")}


def add_question(c) -> Path:
    con = pick_concept(c)
    xl = pick_from("选 X 列（问题类型）", [(lv["key"], f'X{lv["x"]} {lv["label"]}') for lv in c.axes["x_axis"]["levels"]])
    yl = pick_from("选 Y 层（追问层次）", [(lv["key"], f'Y{lv["y"]} {lv["label"]}') for lv in c.axes["y_axis"]["levels"]])
    xmap = {lv["key"]: lv["x"] for lv in c.axes["x_axis"]["levels"]}
    ymap = {lv["key"]: lv["y"] for lv in c.axes["y_axis"]["levels"]}
    text = ask("问题文字")
    note = ask("这道题想追问什么（一句话，可留空）", "")
    qid = f"{xl}.{yl}"
    payload = {
        "schema": "question/v3", "id": qid, "concept_id": con.id,
        "x": xmap[xl], "y": ymap[yl], "text": text, "note": note,
        "author": author_block(), "created_at": date.today().isoformat(),
    }
    return write_card(DATA / con.id / "questions", f"q.{qid}", payload)


def add_canonical(c) -> Path:
    con = pick_concept(c)
    qid = pick_from("为哪道题认定正确答案", [(q["id"], q["text"]) for q in con.questions])
    if con.canonicals_of(qid):
        print("这道题已经有正确答案了。不要新建第二份，请直接修改现有 canon 并在 PR 里说明依据。")
        sys.exit(1)
    basis = ask("认定依据（为什么这一组要点算正确，必填）")
    print("逐条输入这道题的正确答案必须守住的要点，空行结束（至少一条）：")
    invs = []
    while True:
        line = input(f"  i{len(invs) + 1}: ").strip()
        if not line:
            break
        invs.append({"id": f"i{len(invs) + 1}", "claim": line})
    cid = f"c.{qid}"
    payload = {
        "schema": "canonical/v3", "id": cid, "question_id": qid,
        "label": "正确答案要点", "invariants": invs, "basis": basis,
        "author": author_block(),
        "review": {
            "status": "pending", "by": "", "at": "",
            "policy": "改动本文件须 code owner 审核",
        },
        "created_at": date.today().isoformat(), "status": "canonical",
    }
    p = write_card(DATA / con.id / "canonical", cid, payload)
    print("\n注意：这份 canon 是 pending，validate.py 会拦下它。")
    print("请在 PR 里写明认定依据并 @simple-calcate 审核；审核通过后把")
    print("review.status 改为 approved、补上 review.by / review.at，CI 才会转绿。")
    return p


def add_answer(c) -> Path:
    con = pick_concept(c)
    qid = pick_from("回答哪个问题", [(q["id"], q["text"]) for q in con.questions])
    cans = con.canonicals_of(qid)
    if not cans:
        print("这道题还没有经认定的正确答案，请先运行 python3 tools/new_card.py canonical")
        sys.exit(1)
    canon = cans[0]
    style = ask("这条答案的表达风格（如 平实叙述 / 比喻 / 分点说明）")
    register = ask("语调（如 说明文 / 口语 / 议论文）", "说明文")
    print("输入答案正文，可多行，空行结束：")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line.strip())
    content = "".join(lines)
    note = ask("出处或说明（必填，原创就写原创）")
    covers = [i["id"] for i in canon.get("invariants", [])]
    existing = con.answers_of(qid)
    used = [int(a["id"].rsplit(".", 1)[-1]) for a in existing
            if a["id"].rsplit(".", 1)[-1].isdigit()]
    aid = f"{qid}.{max(used, default=0) + 1:02d}"
    payload = {
        "schema": "answer/v3", "id": aid,
        "concept_id": con.id, "question_id": qid, "canonical_id": canon["id"],
        "style": style, "register": register, "content": content,
        "covers": covers,
        "author": author_block(),
        "source": {"type": "original", "note": note},
        "created_at": date.today().isoformat(), "status": "published",
    }
    p = write_card(DATA / con.id / "answers", f"a.{aid}", payload)
    print(f"\n已自动覆盖 {len(covers)} 条正确要点：{', '.join(covers)}")
    print("写完正文后确认每条要点都还守得住，再跑 validate.py。")
    return p


def pick_concept(c):
    opts = [(con.id, con.meta["term"]) for con in c.concepts]
    if len(opts) == 1:
        return c.concepts[0]
    cid = pick_from("选概念", opts)
    return next(con for con in c.concepts if con.id == cid)


def main() -> int:
    c = Corpus()
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    if not kind:
        kind = pick_from("要加哪一类卡片", [
            ("answer", "一条同义改写（最常见，无需审核）"),
            ("question", "一个新问题"),
            ("canonical", "一份正确答案（须审核）"),
        ])
    builders = {"answer": add_answer, "question": add_question, "canonical": add_canonical}
    if kind not in builders:
        print("只支持 answer / question / canonical")
        return 1
    p = builders[kind](c)
    print(f"\n已生成 {p.relative_to(ROOT)}")
    print("下一步：打开它把内容写好，再跑 python3 pipeline/validate.py 自检。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
