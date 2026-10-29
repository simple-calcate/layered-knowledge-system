#!/usr/bin/env python3
"""export_training.py — 把两层数据分流导出成训练样本。

核心分工（混在一起训就废了）：

  第一层 知识平面 -> recall.jsonl
    目标：精确召回、零幻觉。
    做法：同一条 strict_definition 做多种「寻址变换」——直陈、坐标寻址、
    完形填空、反问答名、前置邻接、公式列举、族/层枚举。
    ⚠ 这里刻意**不**做「换个说法重写定义」。定义层一旦改写，就失去了锚点意义。
    泛化能力的培养全部交给第二层。

  第二层 习题池 -> generalize_sft.jsonl + generalize_group.jsonl
    目标：同一个解题骨架，多种表面表达。
    做法：每道题的 N 个变体展开成 N 条 SFT 样本（打散后模型学不到固定句式）；
    同时把同题变体成组输出，用于 GRPO / KTO / DPO 的组内偏好对齐。

  另有 skeleton_probe.jsonl：反过来由作答还原骨架步骤，
  用来训练并检测「看穿表达、抓到不变量」的能力。

用法：
  PYTHONPATH=pipeline python3 pipeline/export_training.py --topic backprop
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys_path = ROOT / "pipeline"

import sys  # noqa: E402

sys.path.insert(0, str(sys_path))

from ksys import Topic, content_hash, terminal_closure  # noqa: E402

CLOZE = "____"


def technical_token(definition: str, term: str) -> str | None:
    """挑一个适合做空格的技术词：优先术语本身，其次最长的英文符号。"""
    if term and term in definition:
        return term
    en = re.findall(r"[A-Za-z][A-Za-z_\-]{3,}", definition)
    if en:
        return max(en, key=len)
    zh = re.findall(r"[\u4e00-\u9fff]{4,6}", definition)
    return max(zh, key=len) if zh else None


def term_of(node: dict) -> str:
    """知识点的规范术语。

    knowledge.term 是可选字段；没写时用 title 兜底，保证导出永远有值。
    """
    return node["knowledge"].get("term", node["title"])


def recall_samples(t: Topic) -> list[dict]:
    out: list[dict] = []
    for n in t.nodes:
        k = n["knowledge"]
        term = term_of(n)
        dfn = k["strict_definition"]
        x, y = t.canvas(n)
        fam = t.families[n["family_key"]]
        strat = t.strata[n["stratum"]]
        base = {
            "node_id": n["id"],
            "family_key": n["family_key"],
            "family_label": fam["label"],
            "stratum": n["stratum"],
            "stratum_label": strat["label"],
            "coordinate": {"x": x, "y": y},
            "canonical_version": n.get("version", 1),
            "definition_hash": content_hash(dfn),
            "layer": "knowledge_plane",
            "objective": "memorization",
        }

        out.append({
            **base,
            "task": "term_to_definition",
            "instruction": f"给出「{term}」的严格定义。要求逐字准确，不得改写或省略。",
            "input": "",
            "output": dfn,
        })

        out.append({
            **base,
            "task": "coordinate_to_definition",
            "instruction": (
                f"在主题《{t.meta.get('title')}》的知识平面上，坐标 ({x}, {y}) "
                f"（X 广度「{fam['label']}」，Y 深度「{strat['label']}」）上的知识点是什么？给出它的严格定义。"
            ),
            "input": "",
            "output": f"{term}\n\n{dfn}",
        })

        tok = technical_token(dfn, term)
        if tok:
            out.append({
                **base,
                "task": "cloze",
                "instruction": f"下面是「{term}」的定义，其中关键术语被替换为 {CLOZE}，请填回原词，只输出该词。",
                "input": dfn.replace(tok, CLOZE, 1),
                "output": tok,
            })

        out.append({
            **base,
            "task": "definition_to_term",
            "instruction": "下面是一段严格定义，请回答它定义的是哪个概念，只输出概念名。",
            "input": dfn,
            "output": term,
        })

        pre = [
            term_of(t.nodes_by_id[p])
            for p in n.get("links", {}).get("prerequisites", [])
            if p in t.nodes_by_id
        ]
        out.append({
            **base,
            "task": "prerequisites",
            "instruction": f"要理解「{term}」，必须先掌握哪些前置概念？按次序列出。",
            "input": "",
            "output": "、".join(pre) if pre else "（本主题入口，无前置）",
        })

        if k.get("key_formulas"):
            out.append({
                **base,
                "task": "key_formulas",
                "instruction": f"写出「{term}」涉及的核心公式或式子。",
                "input": "",
                "output": "\n".join(f"$${f}$$" for f in k["key_formulas"]),
            })

        if k.get("boundary"):
            out.append({
                **base,
                "task": "boundary",
                "instruction": f"「{term}」在什么条件下不成立或需要修正？",
                "input": "",
                "output": k["boundary"],
            })

    # 族 / 层枚举：训练对整个二维结构的整体把握
    for fam in t.axes["x_axis"]["families"]:
        titles = [term_of(n) for n in t.nodes if n["family_key"] == fam["key"]]
        if titles:
            out.append({
                "task": "family_enumeration",
                "layer": "knowledge_plane",
                "objective": "memorization",
                "family_key": fam["key"],
                "node_id": "",
                "instruction": f"列出主题《{t.meta.get('title')}》中「{fam['label']}」这一族（X={fam['x']}）包含的全部知识点。",
                "input": "",
                "output": "、".join(titles),
            })
    for lv in t.axes["y_axis"]["levels"]:
        titles = [term_of(n) for n in t.nodes if n["stratum"] == lv["value"]]
        if titles:
            out.append({
                "task": "stratum_enumeration",
                "layer": "knowledge_plane",
                "objective": "memorization",
                "stratum": lv["value"],
                "node_id": "",
                "instruction": (
                    f"列出主题《{t.meta.get('title')}》中位于第 {lv['value']} 个机制层"
                    f"（{lv['label']}）的全部知识点。"
                ),
                "input": "",
                "output": "、".join(titles),
            })
    return out


def generalization_samples(t: Topic) -> tuple[list[dict], list[dict], list[dict]]:
    sft: list[dict] = []
    groups: list[dict] = []
    probes: list[dict] = []

    for e in t.exercises:
        node_ids = e["node_id"] if isinstance(e["node_id"], list) else [e["node_id"]]
        terms = [term_of(t.nodes_by_id[i]) for i in node_ids if i in t.nodes_by_id]
        skeleton_txt = "\n".join(f"{s['id']}. {s['claim']}" for s in e["skeleton"]["steps"])
        required = terminal_closure(e["skeleton"])

        variants = []
        for a in e["answers"]:
            missing = sorted(required - set(a.get("covers_steps", [])))
            variants.append({
                "variant_id": a["variant_id"],
                "style": a.get("style", ""),
                "register": a.get("register", ""),
                "content": a["content"],
            })
            rec = {
                "exercise_id": e["id"],
                "variant_id": a["variant_id"],
                "node_ids": node_ids,
                "node_terms": " / ".join(terms),
                "ex_type": e.get("type", ""),
                "difficulty": e.get("difficulty"),
                "style": a.get("style", ""),
                "register": a.get("register", ""),
                "layer": "exercise_pool",
                "objective": "generalization",
                "instruction": e["stem"],
                "input": "",
                "output": a["content"],
                "covers_steps": a.get("covers_steps", []),
                "missing_steps": missing,
            }
            if missing:
                rec["REJECTED_BY_VALIDATOR"] = True
            sft.append(rec)

            probes.append({
                "exercise_id": e["id"],
                "variant_id": a["variant_id"],
                "layer": "exercise_pool",
                "task": "answer_to_skeleton",
                "instruction": "把下面这段解答还原成它背后的解题骨架，按顺序列出每一步的断言。",
                "input": a["content"],
                "output": skeleton_txt,
            })

        groups.append({
            "exercise_id": e["id"],
            "node_ids": node_ids,
            "node_terms": " / ".join(terms),
            "layer": "exercise_pool",
            "objective": "group_preference",
            "prompt": e["stem"],
            "chosen_group": variants,
            "group_size": len(variants),
            "skeleton": skeleton_txt,
            "negative_policy": (
                "组内各答案共享同一解题骨架，互为等价正例；"
                "若需负样本，应取其它习题的答案作为错配负例，而不是把组内任一答案降级。"
            ),
        })
    return sft, groups, probes


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="backprop")
    ap.add_argument("--out-dir", default=str(ROOT / "out" / "training"))
    args = ap.parse_args()

    t = load_topic_safe(args.topic)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    recall = recall_samples(t)
    sft, groups, probes = generalization_samples(t)

    write_jsonl(out_dir / "recall.jsonl", recall)
    write_jsonl(out_dir / "generalize_sft.jsonl", sft)
    write_jsonl(out_dir / "generalize_group.jsonl", groups)
    write_jsonl(out_dir / "skeleton_probe.jsonl", probes)

    rejected = [r for r in sft if r.get("REJECTED_BY_VALIDATOR")]
    manifest = {
        "topic_id": t.topic_id,
        "title": t.meta.get("title"),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": {
            "recall.jsonl": len(recall),
            "generalize_sft.jsonl": len(sft),
            "generalize_group.jsonl": len(groups),
            "skeleton_probe.jsonl": len(probes),
        },
        "guard": {
            "rejected_variants": len(rejected),
            "note": (
                "若 rejected_variants > 0，说明有答案没覆盖全部解题不变量。"
                "这些样本已打标但仍写在文件里，正式训练前必须按 REJECTED_BY_VALIDATOR 过滤。"
            ),
        },
        "usage": {
            "recall.jsonl": "低温度 SFT 或高权重重播；另需保留一份 held-out 的坐标->定义召回集做回归门禁",
            "generalize_sft.jsonl": "普通 SFT，同一题干的不同变体务必跨 batch 打散",
            "generalize_group.jsonl": "GRPO / KTO / DPO 的组内偏好数据",
            "skeleton_probe.jsonl": "反向任务：由表达还原骨架，用来检测模型是否真学懂而非背模板",
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"导出目录 {out_dir.relative_to(ROOT)}")
    for k, v in manifest["counts"].items():
        print(f"  {k:24} {v:>4} 条")
    if rejected:
        print(f"\n{len(rejected)} 个答案变体未覆盖全部解题不变量，已打标 REJECTED_BY_VALIDATOR")
    else:
        print("\n全部答案变体均覆盖解题不变量，可进训练")
    return 0


def load_topic_safe(topic_id: str) -> Topic:
    return Topic(topic_id)


if __name__ == "__main__":
    raise SystemExit(main())
