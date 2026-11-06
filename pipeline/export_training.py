#!/usr/bin/env python3
"""export_training.py — 把概念问题网导出成训练样本。

v3 的训练目标只有两件事：
  A. 记住问题网的结构，以及每道题唯一那个经审核认定的正确答案
  B. 学会「同一个正确意思可以换很多种说法」，而不被措辞困住

**不导出任何未采纳的说法**：与正确答案冲突的内容放在 archive/ 下，
不在加载范围内；漏掉要点的改写也会被直接丢弃，不写进任何分片。

四个分片：
  recall.jsonl            结构记忆 + 正确答案要点背诵
  generalize_sft.jsonl    一题多答：每条 = 合格的一条同义改写
  generalize_group.jsonl  每题一组的 chosen，供 GRPO / DPO / KTO
  invariant_probe.jsonl   反向任务：由答案还原要点，检测是否真读懂（评测用）
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ksys import Corpus, ROOT, content_hash  # noqa: E402


def inv_lines(canon: dict) -> str:
    return "\n".join(f"- {i['id']}：{i['claim']}" for i in canon.get("invariants", []))


def recall_rows(c: Corpus, views: list) -> list[dict]:
    out: list[dict] = []
    by_concept: dict[str, list] = {}
    for con, q, canon, answers in views:
        by_concept.setdefault(con.id, []).append((con, q, canon, answers))

    for cid, items in by_concept.items():
        con = items[0][0]
        term = con.meta["term"]
        x_of, y_of = c.x_levels, c.y_levels
        base = {"concept_id": cid, "term": term, "objective": "structure_recall"}

        all_q = [f"X{q['x']}Y{q['y']} {q['text']}" for _, q, _, _ in items]
        out.append({**base, "task": "concept_to_questions",
                    "instruction": f"围绕名词「{term}」，列出当前知识网中已收录的全部问题（含坐标）。",
                    "input": "", "output": "\n".join(all_q)})

        for _, q, canon, _ in items:
            xl, yl = x_of[q["x"]]["label"], y_of[q["y"]]["label"]
            common = {**base, "question_id": q["id"], "coordinate": {"x": q["x"], "y": q["y"]},
                      "question_hash": content_hash(q["text"])}
            out.append({**common, "task": "coordinate_to_question",
                        "instruction": f"在「{term}」的问题网上，X{q['x']}（{xl}）× Y{q['y']}（{yl}）这一格问的是什么？",
                        "input": "", "output": q["text"]})
            out.append({**common, "task": "question_to_coordinate",
                        "instruction": f"「{term}」的问题「{q['text']}」位于问题网的哪一格？只输出 X?Y?。",
                        "input": "", "output": f"X{q['x']}Y{q['y']}"})
            if q.get("note"):
                out.append({**common, "task": "question_intent",
                            "instruction": f"「{q['text']}」这道题想追问什么？",
                            "input": "", "output": q["note"]})
            if canon:
                out.append({**common, "task": "question_to_correct_points",
                            "objective": "canonical_recall",
                            "canonical_id": canon["id"],
                            "instruction": f"「{q['text']}」这道题的正确答案必须守住哪几条要点？逐条列出。",
                            "input": "", "output": inv_lines(canon)})

        for x, lv in x_of.items():
            qs = [q["text"] for _, q, _, _ in items if q["x"] == x]
            if qs:
                out.append({**base, "task": "axis_enumeration", "axis": "X", "value": x,
                            "instruction": f"「{term}」的问题网里，X{x}「{lv['label']}」这一列有哪些问题？",
                            "input": "", "output": "\n".join(qs)})
        for y, lv in y_of.items():
            qs = [q["text"] for _, q, _, _ in items if q["y"] == y]
            if qs:
                out.append({**base, "task": "axis_enumeration", "axis": "Y", "value": y,
                            "instruction": f"「{term}」的问题网里，Y{y}「{lv['label']}」这一层有哪些问题？",
                            "input": "", "output": "\n".join(qs)})
    return out


def generalization_rows(views: list):
    sft: list[dict] = []
    groups: list[dict] = []
    probes: list[dict] = []
    excluded = 0
    for con, q, canon, answers in views:
        if not canon:
            continue
        inv = canon.get("invariants", [])
        inv_text = inv_lines(canon)
        inv_ids = [i["id"] for i in inv]
        chosen: list[str] = []
        for a in answers:
            if a["misses"]:
                excluded += 1
                continue
            sft.append({
                "question_id": q["id"],
                "concept_id": con.id,
                "term": con.meta["term"],
                "coordinate": {"x": q["x"], "y": q["y"]},
                "question": q["text"],
                "canonical_id": canon["id"],
                "style": a.get("style", ""),
                "register": a.get("register", ""),
                "answer_id": a["id"],
                "answer_hash": content_hash(a["content"]),
                "author": a.get("author", {}),
                "source": a.get("source", {}),
                "invariant_ids": inv_ids,
                "instruction": q["text"],
                "input": "",
                "output": a["content"],
            })
            chosen.append(a["content"])
            probes.append({
                "task": "answer_to_invariants",
                "concept_id": con.id,
                "question_id": q["id"],
                "answer_id": a["id"],
                "instruction": "下面这段答案必须守住哪几条正确要点？逐条列出。",
                "input": a["content"],
                "output": inv_text,
            })
        if chosen:
            groups.append({
                "question_id": q["id"],
                "concept_id": con.id,
                "term": con.meta["term"],
                "coordinate": {"x": q["x"], "y": q["y"]},
                "question": q["text"],
                "canonical_id": canon["id"],
                "invariants": inv,
                "chosen": chosen,
                "note": "每题只有这一组；不存在第二个 chosen 组，未采纳说法不导出",
            })
    return sft, groups, probes, excluded


def write_jsonl(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "out" / "training"))
    args = ap.parse_args()

    c = Corpus()
    views = list(c.views())
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    recall = recall_rows(c, views)
    sft, groups, probes, excluded = generalization_rows(views)
    write_jsonl(out / "recall.jsonl", recall)
    write_jsonl(out / "generalize_sft.jsonl", sft)
    write_jsonl(out / "generalize_group.jsonl", groups)
    write_jsonl(out / "invariant_probe.jsonl", probes)

    manifest = {
        "model": "concept-question-answer/v3",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "note": "每题只有一个经审核认定的正确答案；只有它的同义改写进入训练，任何未采纳说法都不导出。",
        "counts": {
            "recall.jsonl": len(recall),
            "generalize_sft.jsonl": len(sft),
            "generalize_group.jsonl": len(groups),
            "invariant_probe.jsonl": len(probes),
        },
        "guard": {
            "excluded_unadopted": True,
            "note": "archive/unadopted/ 不在加载范围内；被认定为冲突的说法不进入任何分片。",
            "excluded_incomplete_answers": excluded,
            "note2": "漏掉正确要点的改写被直接丢弃，不写入分片，也不打标记留在文件里。",
        },
        "usage": {
            "recall.jsonl": "低温度 SFT / 高权重重播，记住问题网结构与每题唯一正确要点",
            "generalize_sft.jsonl": "普通 SFT；同一题的不同改写务必跨 batch 打散，防止背模板",
            "generalize_group.jsonl": "GRPO / DPO / KTO 的组内偏好；每题只有一个 chosen 组",
            "invariant_probe.jsonl": "评测用反向任务，检测模型是否守住正确要点，不参与训练",
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"导出目录 {out.relative_to(ROOT)}")
    for k, v in manifest["counts"].items():
        print(f"  {k:26} {v:>4} 条")
    print(f"被丢弃的不完整改写 {excluded} 条（未写入任何分片）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
