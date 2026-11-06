#!/usr/bin/env python3
"""export_app.py — 把 data/concepts/ 下的卡片打包成前端唯一消费的 corpus.json。

前端**只**读 web/data/corpus.json，不直接读 data/。
数据层的字段可以随意重构，前端契约只有这一处。

只导出经审核认定的正确答案及其同义改写；archive/ 下的未采纳说法不在加载范围内。

用法：python3 pipeline/export_app.py [--concept knowledge]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ksys import Corpus, ROOT, content_hash  # noqa: E402


def build(concept_id: str = "") -> dict:
    c = Corpus()
    x_of = {lv["x"]: lv for lv in c.axes["x_axis"]["levels"]}
    y_of = {lv["y"]: lv for lv in c.axes["y_axis"]["levels"]}

    concepts_meta = [{**con.meta, "question_count": len(con.questions)} for con in c.concepts]
    primary = next((con for con in c.concepts if con.id == concept_id), None) or (c.concepts[0] if c.concepts else None)

    questions = []
    for con, q, canon, answers in c.views():
        if concept_id and con.id != concept_id:
            continue
        canon_out = None
        if canon:
            canon_out = {
                "id": canon["id"],
                "invariants": canon.get("invariants", []),
                "basis": canon.get("basis", ""),
                "author": canon.get("author", {}),
                "review": canon.get("review", {}),
            }
        answers_out = [
            {
                "id": a["id"],
                "style": a.get("style", ""),
                "register": a.get("register", ""),
                "content": a["content"],
                "content_hash": content_hash(a["content"]),
                "covers": a.get("covers", []),
                "misses": a["misses"],
                "author": a.get("author", {}),
                "source": a.get("source", {}),
                "created_at": a.get("created_at", ""),
            }
            for a in answers
        ]
        x, y = q["x"], q["y"]
        questions.append({
            "id": q["id"],
            "concept_id": con.id,
            "x": x, "y": y,
            "breadth_label": x_of[x]["label"],
            "depth_label": y_of[y]["label"],
            "text": q["text"],
            "note": q.get("note", ""),
            "author": q.get("author", {}),
            "created_at": q.get("created_at", ""),
            "canonical": canon_out,
            "answers": answers_out,
            "has_canonical": canon_out is not None,
            "answer_count": len(answers_out),
        })

    questions.sort(key=lambda q: (q["x"], q["y"]))
    n_canons = sum(1 for q in questions if q["has_canonical"])
    n_answers = sum(q["answer_count"] for q in questions)
    cells = len(x_of) * len(y_of)

    app = {
        "title": (primary.meta.get("term", "概念知识网") + " · 二维问题网") if primary else "概念知识网",
        "subtitle": primary.meta.get("summary", "") if primary else "",
        "version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_path": "data/concepts",
        "axes": {
            "x_label": c.axes["x_axis"]["name"],
            "y_label": c.axes["y_axis"]["name"],
            "x_list": [{"x": lv["x"], "key": lv["key"], "label": lv["label"], "desc": lv["desc"]} for lv in c.axes["x_axis"]["levels"]],
            "y_list": [{"y": lv["y"], "key": lv["key"], "label": lv["label"], "desc": lv["desc"]} for lv in c.axes["y_axis"]["levels"]],
        },
        "gap_policy": c.axes.get("gap_policy", ""),
    }

    return {
        "app": app,
        "concept": primary.meta if primary else {},
        "concepts": concepts_meta,
        "questions": questions,
        "stats": {
            "concepts": len(c.concepts),
            "questions": len(questions),
            "canonicals": n_canons,
            "answers": n_answers,
            "cells_filled": len({(q["x"], q["y"]) for q in questions}),
            "cells_total": cells,
            "cells_open": cells - len({(q["x"], q["y"]) for q in questions}),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concept", default="")
    ap.add_argument("--out", default=str(ROOT / "web" / "data" / "corpus.json"))
    args = ap.parse_args()

    payload = build(args.concept)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = payload["stats"]
    print(f"已生成 {out.relative_to(ROOT)}")
    print(f"  概念 {s['concepts']} / 问题 {s['questions']} / 正确答案 {s['canonicals']} / 同义改写 {s['answers']}")
    print(f"  已占格 {s['cells_filled']} / {s['cells_total']}，空缺 {s['cells_open']} 格留给贡献者")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
