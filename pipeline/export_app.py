#!/usr/bin/env python3
"""export_app.py — 把 data/topics/<topic>/ 下的源数据打包成前端唯一消费的 corpus.json。

前端**只**读 web/data/corpus.json，不直接读 data/。
这样数据层的字段可以随意重构，前端契约只有这一处。

用法：
  PYTHONPATH=pipeline python3 pipeline/export_app.py --topic backprop
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from ksys import Topic, terminal_closure  # noqa: E402


def build(topic_id: str) -> dict:
    t = Topic(topic_id)
    fam_label = {f["key"]: f["label"] for f in t.axes["x_axis"]["families"]}
    strat_label = {lv["value"]: lv["label"] for lv in t.axes["y_axis"]["levels"]}
    x_of = t.x_of_family

    app = {
        "topic_id": t.topic_id,
        "title": t.meta.get("title", t.topic_id),
        "subtitle": t.meta.get("subtitle", ""),
        "version": t.meta.get("version", 1),
        "updated_at": t.meta.get("updated_at", ""),
        "source_path": str(t.dir.relative_to(ROOT)),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "description": t.meta.get("description", ""),
        "axes": {
            "x_label": t.axes["x_axis"].get("name", "广度轴"),
            "y_label": t.axes["y_axis"].get("name", "深度轴"),
            "x_list": [
                {"key": f["key"], "x": f["x"], "label": f["label"], "desc": f.get("desc", "")}
                for f in t.axes["x_axis"]["families"]
            ],
            "x_families": [
                {"key": f["key"], "x": f["x"], "label": f["label"], "desc": f.get("desc", "")}
                for f in t.axes["x_axis"]["families"]
            ],
            "y_list": [
                {"value": lv["value"], "key": lv["key"], "label": lv["label"], "desc": lv.get("desc", "")}
                for lv in t.axes["y_axis"]["levels"]
            ],
        },
        "conventions": t.meta.get("conventions", {}),
        "authoring_rules": t.meta.get("authoring_rules", []),
    }

    nodes = []
    for n in sorted(t.nodes, key=lambda n: (n["stratum"], x_of[n["family_key"]])):
        k = n["knowledge"]
        x, y = t.canvas(n)
        nodes.append({
            "id": n["id"],
            "title": n["title"],
            "term": k.get("term", n["title"]),
            "focus": k.get("focus", ""),
            "strict_definition": k["strict_definition"],
            "core_mechanics": k["core_mechanics"],
            "key_formulas": k.get("key_formulas", []),
            "boundary": k.get("boundary", ""),
            "intuition": k.get("intuition", ""),
            "tags": n.get("tags", []),
            "status": n.get("status", "published"),
            "version": n.get("version", 1),
            "family_key": n["family_key"],
            "family_label": fam_label.get(n["family_key"], n["family_key"]),
            "stratum": n["stratum"],
            "stratum_label": strat_label.get(n["stratum"], str(n["stratum"])),
            "x": x,
            "y": y,
            "breadth_label": fam_label.get(n["family_key"], n["family_key"]),
            "depth_label": strat_label.get(n["stratum"], str(n["stratum"])),
            "plane_coordinate": {
                "x": x,
                "y": y,
                "breadth_label": fam_label.get(n["family_key"], n["family_key"]),
                "depth_label": strat_label.get(n["stratum"], str(n["stratum"])),
            },
            "prerequisites": n.get("links", {}).get("prerequisites", []),
            "extends": n.get("links", {}).get("extends", []),
            "related": n.get("links", {}).get("related", []),
            "prerequisite_refs": k.get("prerequisite_refs", []),
            "exercise_ids": n.get("exercise_refs", []),
        })

    exercises = []
    for e in t.exercises:
        required = terminal_closure(e["skeleton"])
        node_ids = e["node_id"] if isinstance(e["node_id"], list) else [e["node_id"]]
        exercises.append({
            "id": e["id"],
            "node_ids": node_ids,
            "primary_node_id": node_ids[0],
            "ex_type": e.get("type", ""),
            "title": e.get("title", ""),
            "difficulty": e.get("difficulty"),
            "stem": e["stem"],
            "hints": e.get("hints", []),
            "semantic_invariants": [s["claim"] for s in e["skeleton"]["steps"]],
            "invariant_ids": [s["id"] for s in e["skeleton"]["steps"]],
            "checks": e.get("checks", []),
            "answers": [
                {
                    "variant_id": a["variant_id"],
                    "style": a.get("style", ""),
                    "register": a.get("register", ""),
                    "content": a["content"],
                    "covers_steps": a.get("covers_steps", []),
                    "misses_steps": sorted(required - set(a.get("covers_steps", []))),
                }
                for a in e["answers"]
            ],
        })

    cheatsheet = [
        {
            "node_id": n["id"],
            "title": n["title"],
            "term": n["knowledge"].get("term", n["title"]),
            "focus": n["knowledge"].get("focus", ""),
        }
        for n in t.nodes
    ]

    return {
        "app": app,
        "nodes": nodes,
        "exercises": exercises,
        "cheatsheet": cheatsheet,
        "stats": {
            "nodes": len(nodes),
            "exercises": len(exercises),
            "answer_variants": sum(len(e["answers"]) for e in exercises),
            "families": len(app["axes"]["x_list"]),
            "strata": len(app["axes"]["y_list"]),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="backprop")
    ap.add_argument("--out", default=str(ROOT / "web" / "data" / "corpus.json"))
    args = ap.parse_args()

    payload = build(args.topic)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    s = payload["stats"]
    print(f"已生成\t{out.relative_to(ROOT)}")
    print(f"\tnodes     \t{s['nodes']}")
    print(f"\tfamilies  \t{s['families']} × strata {s['strata']}")
    print(f"\texercises \t{s['exercises']}")
    print(f"\tvariants  \t{s['answer_variants']}")
    print("注意：该文件是构建产物，改数据请改 data/ 后重跑本脚本")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
