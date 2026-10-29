#!/usr/bin/env python3
"""validate.py — 双层知识体系的一次性质检门禁。

跑五件事：
  1. 主题与标尺：topic.json / axes 文件能否加载、required 字段是否齐
  2. 知识平面：id 唯一、(family, stratum) 不重叠、连边是否指向真实节点
  3. 习题池：node 是否落后至少一个配套习题、skeleton 是否是有向无环图
  4. 一题多解：每个解答变体是否覆盖了「终局步骤 + 其依赖闭包」
  5. 可执行印证：question.checks 里的 Python 断言直接跑一遍

用法：
    PYTHONPATH=pipeline python3 pipeline/validate.py --topic backprop
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from ksys import (  # noqa: E402
    find_garbage,
    has_cycle,
    iter_strings,
    run_checks,
    terminal_closure,
    Topic,
)

TOPIC_REQUIRED = ("schema", "id", "title", "version", "updated_at", "language", "math_flavor")
NODE_REQUIRED_K = ("intuition", "strict_definition", "core_mechanics", "boundary")



def check_topic(t: Topic, errors: list[str], warnings: list[str]) -> None:
    for field in TOPIC_REQUIRED:
        if not t.meta.get(field):
            errors.append(f"[topic] 缺少必填字段 {field}")

    x_axis = t.axes.get("x_axis", {})
    y_axis = t.axes.get("y_axis", {})
    if not x_axis.get("families"):
        errors.append("[axes] x_axis.families 为空，广度轴无标尺")
    fam_x = {}
    for fam in x_axis.get("families", []):
        if fam.get("x") in fam_x:
            errors.append(f"[axes] 广度档位 {fam['x']} 被重复使用")
        fam_x[fam.get("x")] = fam.get("key")
    seen_stratum = set()
    for lv in y_axis.get("levels", []):
        if lv.get("value") in seen_stratum:
            errors.append(f"[axes] 机制层 {lv['value']} 重复")
        seen_stratum.add(lv.get("value"))


def check_plane(t: Topic, errors: list[str], warnings: list[str]) -> None:
    fam_x = {f["key"]: f["x"] for f in t.axes["x_axis"]["families"]}
    fam_label = {f["key"]: f["label"] for f in t.axes["x_axis"]["families"]}
    seen_cells: dict[tuple[int, int], str] = {}
    row_of = {lv["value"]: lv for lv in t.axes["y_axis"]["levels"]}

    # 先把全部 id 收齐，否则后面的连边校验会误报「节点不存在」
    all_ids: set[str] = {n.get("id") for n in t.nodes}
    seen_ids: dict[str, int] = {i: 0 for i in all_ids}

    for n in t.nodes:
        nid = n.get("id", "<missing id>")
        seen_ids[nid] += 1
        fk = n.get("family_key")
        st = n.get("stratum")
        if fk not in fam_x:
            errors.append(f"[plane] {nid}: family_key 不存在：{fk}")
            continue
        if st not in row_of:
            errors.append(f"[plane] {nid}: stratum 不在定义范围内：{st}")
            continue

        cell = (fam_x[fk], st)
        if cell in seen_cells:
            errors.append(f"[plane] {nid}: 與 {seen_cells[cell]} 占用同一个格子 {cell}")
        else:
            seen_cells[cell] = nid

        pc = n.get("plane_coordinate") or {}
        if not pc:
            warnings.append(f"[plane] {nid}: 缺 plane_coordinate 字段")
        else:
            if (pc.get("x"), pc.get("y")) != cell:
                errors.append(f"[plane] {nid}: plane_coordinate {(pc.get('x'), pc.get('y'))} != 派生的 {cell}")

        k = n.get("knowledge", {})
        for field in NODE_REQUIRED_K:
            if not k.get(field):
                warnings.append(f"[plane] {nid}: knowledge.{field} 为空")

        for kind in ("prerequisites", "extends", "related"):
            for ref in n.get("links", {}).get(kind, []):
                if ref not in seen_ids:
                    errors.append(f"[plane] {nid}: links.{kind} 指向不存在的节点 {ref}")

        if n.get("exercise_refs") is None:
            warnings.append(f"[plane] {nid}: 未挂载任何习题")

    for nid, cnt in seen_ids.items():
        if cnt > 1:
            errors.append(f"[plane] 节点 id 重复：{nid}")

    for fam_key, x in fam_x.items():
        rows = [st for (fx, st) in seen_cells if fx == x]
        members = [n for n in t.nodes if n.get("family_key") == fam_key]
        if len(members) != len(rows):
            warnings.append(f"[plane] 族 {fam_key} 有 {len(members)} 个节点，但只占 {len(rows)} 个格子")
        if not members:
            warnings.append(
                f"[plane] 族 {fam_key}（{fam_label.get(fam_key, fam_key)}）在画布上为空，"
                f"若确无此族内容请从 axes 里移除该列"
            )


def check_pool(t: Topic, errors: list[str], warnings: list[str]) -> None:
    ex_ids: dict[str, int] = {}
    for e in t.exercises:
        eid = e.get("id", "<missing id>")
        ex_ids[eid] = ex_ids.get(eid, 0) + 1
        nid = e.get("node_id")
        if nid not in {n["id"] for n in t.nodes}:
            errors.append(f"[pool] {eid}: node_id 不存在：{nid}")
            continue
        node_of = next((n for n in t.nodes if n["id"] == nid), None)
        if node_of is not None:
            refs = node_of.get("exercise_refs") or []
            if eid not in refs:
                warnings.append(f"[pool] {eid}: 未在 {nid} 的 exercise_refs 中登记")
            for missing in refs:
                if missing not in ex_ids and missing not in {x.get("id") for x in t.exercises}:
                    errors.append(f"[pool] {nid}: exercise_refs 指向不存在的习题 {missing}")

        sk = e.get("skeleton", {})
        steps = sk.get("steps", [])
        step_ids = [s.get("id") for s in steps]
        if len(set(step_ids)) != len(step_ids):
            errors.append(f"[pool] {eid}: skeleton.step id 重复: {step_ids}")
        # step 的依赖必须指向存在的 step
        for s in steps:
            for dep in s.get("depends_on", []):
                if dep not in step_ids:
                    errors.append(f"[pool] {eid}: step {s.get('id')} 依赖了不存在的 step {dep}")

        if not steps:
            errors.append(f"[pool] {eid}: skeleton.steps 为空")

        cycle = has_cycle(sk)
        if cycle:
            errors.append(f"[pool] {eid}: skeleton 存在循环依赖 {' -> '.join(cycle)}")

        term = sk.get("terminal_steps") or []
        for tid in term:
            if tid not in step_ids:
                errors.append(f"[pool] {eid}: terminal_steps 含未知 step {tid}")

        answers = e.get("answers", [])
        if len(answers) < 3:
            warnings.append(f"[pool] {eid}: 只有 {len(answers)} 个解答变体，建议至少 3 个")

        closure = terminal_closure(sk)
        for a in answers:
            covers = set(a.get("covers_steps") or [])
            unknown = covers - set(step_ids)
            if unknown:
                errors.append(f"[pool] {eid}/{a.get('variant_id')}: covers_steps 含未知 step {sorted(unknown)}")
            missing = closure - covers
            if missing:
                errors.append(
                    f"[pool] {eid}/{a.get('variant_id')}: 未覆盖终局步骤闭包 {sorted(missing)}"
                )
            if not (a.get("content") or "").strip():
                errors.append(f"[pool] {eid}/{a.get('variant_id')}: content 为空")

        covered_all = set()
        for a in answers:
            covered_all |= set(a.get("covers_steps") or [])
        gaps = closure - covered_all
        unused = set(step_ids) - covered_all
        if gaps:
            errors.append(f"[pool] {eid}: 终局步骤没有被任何解答覆盖 {sorted(gaps)}")
        for uid in sorted(unused):
            warnings.append(f"[pool] {eid}: step {uid} 未被任何解答覆盖（非终局步骤，允许但不常见）")

    for eid, cnt in ex_ids.items():
        if cnt > 1:
            errors.append(f"[pool] 习题 id 重复: {eid}")

    exercised = {e.get("node_id") for e in t.exercises}
    for n in t.nodes:
        n_ex = [e for e in t.exercises if e.get("node_id") == n["id"]]
        if not n_ex:
            warnings.append(f"[pool] 节点 {n['id']} 尚无配套习题")


def run_executable_checks(t: Topic, errors: list[str], warnings: list[str]) -> None:
    exercised = 0
    for e in t.exercises:
        if not e.get("checks"):
            warnings.append(f"[exec] {e.get('id')}: 没有可执行印证，只能用 LLM 评判，不推荐")
            continue
        exercised += 1
        ok, msg = run_checks(e)
        if not ok:
            errors.append(f"[exec] {e.get('id')}: 可执行印证失败 — {msg}")
    print(f"  可执行印证: {exercised}/{len(t.exercises)} 道题带代码校验")


def scan_garbage(t: Topic, errors: list[str], warnings: list[str]) -> None:
    for name, payload in (
        ("topic.json", t.meta),
        ("nodes.json", {"nodes": t.nodes}),
        ("exercises", {"exercises": t.exercises}),
    ):
        for path, text in iter_strings(payload, f"{name}$"):
            for hit in find_garbage(text):
                errors.append(f"[garbage] {path} 疑似乱码片段: {hit!r}")


def main() -> int:
    ap = argparse.ArgumentParser(description="双层知识体系质检门禁")
    ap.add_argument("--topic", default="backprop")
    args = ap.parse_args()

    t = Topic(args.topic)
    errors: list[str] = []
    warnings: list[str] = []

    check_topic(t, errors, warnings)
    check_plane(t, errors, warnings)
    check_pool(t, errors, warnings)
    run_executable_checks(t, errors, warnings)
    scan_garbage(t, errors, warnings)

    fams = len(t.axes["x_axis"]["families"])
    strata = len(t.axes["y_axis"]["levels"])
    answers = sum(len(e.get("answers", [])) for e in t.exercises)
    steps = sum(len(e.get("skeleton", {}).get("steps", [])) for e in t.exercises)

    print(f"\n=== 质检报告：{t.topic_id} ===")
    print(f"  nodes      : {len(t.nodes):>4}   （{fams} 个概念族 × {strata} 个机制层）")
    print(f"  exercises  : {len(t.exercises):>4}   （{answers} 个解答变体，{steps} 条骨架步骤）")
    print(f"  errors     : {len(errors):>4}")
    print(f"  warnings   : {len(warnings):>4}")

    if errors:
        print("\n--- ERROR ---")
        for e in errors:
            print("  " + e)
    if warnings:
        print("\n--- WARN ---")
        for w in warnings:
            print("  " + w)

    if not errors and not warnings:
        print("\n全部通过，无任何告警。")
    print()
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
