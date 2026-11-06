#!/usr/bin/env python3
"""validate.py — 概念知识网的质检门禁。贡献者本地跑、CI 也跑同一份。

检查什么：
  1. 标尺：X/Y 刻度唯一、编号连续可读
  2. 概念：必填字段、id 与目录名一致
  3. 问题：id 唯一、坐标合法、同一格不许塞两个问题
  4. 正确答案：一题最多一个 canon；要点清单、认定依据、审核信息齐全
  5. 同义改写：挂对 canon、覆盖全部要点、署名与出处齐全
  6. 同一题内不许逐字相同（那是复制不是改写）
  7. 乱码扫描：中文里被塞进来的异常西文片段

用法：python3 pipeline/validate.py [--concept knowledge]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ksys import Corpus, ROOT, find_garbage, iter_strings  # noqa: E402

errors: list[str] = []
warnings: list[str] = []


def err(where: str, msg: str):
    errors.append(f"[{where}] {msg}")


def warn(where: str, msg: str):
    warnings.append(f"[{where}] {msg}")


def nonblank(where: str, obj: dict, field: str):
    if not str(obj.get(field, "")).strip():
        err(where, f"缺必填字段 {field}")


def author_ok(where: str, obj: dict):
    a = obj.get("author")
    if not isinstance(a, dict) or not str(a.get("name", "")).strip():
        err(where, "缺 author.name（每条卡片都要有署名）")


def check_axes(c: Corpus):
    for axis, key in (("x_axis", "x"), ("y_axis", "y")):
        levels = c.axes[axis]["levels"]
        vals = [lv[key] for lv in levels]
        if len(vals) != len(set(vals)):
            err("axes", f"{axis} 刻度编号重复")
        if vals != sorted(vals):
            warn("axes", f"{axis} 刻度编号未按升序书写")
        for lv in levels:
            nonblank("axes", lv, "label")


def check_concept(c: Corpus, con):
    w = f"concept/{con.id}"
    nonblank(w, con.meta, "term")
    author_ok(w, con.meta)
    if con.meta.get("id") != con.id:
        err(w, f"concept.json 的 id「{con.meta.get('id')}」与目录名「{con.id}」不一致")


def check_questions(c: Corpus, con):
    seen: Counter = Counter()
    cells: dict[tuple[int, int], str] = {}
    for path, q in con.question_files:
        w = f"q/{path.name}"
        qid = q.get("id", "")
        seen[qid] += 1
        nonblank(w, q, "text")
        author_ok(w, q)
        x, y = q.get("x"), q.get("y")
        if x not in c.x_levels or y not in c.y_levels:
            err(w, f"坐标 ({x}, {y}) 超出标尺范围")
        else:
            cell = (x, y)
            if cell in cells:
                err(w, f"坐标 X{x} Y{y} 已被「{cells[cell]}」占用，一格只放一个问题")
            cells[cell] = qid
    for qid, n in seen.items():
        if n > 1:
            err(f"q/{qid}", f"问题 id 重复 {n} 次")


def check_canonicals(c: Corpus, con):
    seen: Counter = Counter()
    per_question: Counter = Counter()
    for path, s in con.canonical_files:
        w = f"canon/{path.name}"
        sid = s.get("id", "")
        seen[sid] += 1
        nonblank(w, s, "basis")
        author_ok(w, s)
        qid = s.get("question_id")
        if qid not in con.questions_by_id:
            err(w, f"指向不存在的问题 {qid}")
        else:
            per_question[qid] += 1
        if sid != f"c.{qid}":
            warn(w, f"id「{sid}」建议写成 c.{qid}，便于人肉对应")
        invs = s.get("invariants", [])
        if not invs:
            err(w, "没有定义任何要点，同义改写将无从判定")
        iids = [i.get("id") for i in invs]
        if len(iids) != len(set(iids)):
            err(w, "要点 id 重复")
        for i in invs:
            if not str(i.get("claim", "")).strip():
                err(w, f"要点 {i.get('id')} 的 claim 为空")
        review = s.get("review")
        if not isinstance(review, dict) or review.get("status") != "approved":
            err(w, "缺 review.status=approved（正确答案必须经审核认定）")
        elif not str(review.get("by", "")).strip():
            err(w, "缺 review.by（谁审核的）")
    for sid, n in seen.items():
        if n > 1:
            err(f"canon/{sid}", f"正确答案 id 重复 {n} 次")
    for qid, n in per_question.items():
        if n > 1:
            err(f"q/{qid}", f"这道题有 {n} 份正确答案；本库只允许一个，有异议请走 PR 修订原 canon")


def check_answers(c: Corpus, con):
    seen: Counter = Counter()
    for path, a in con.answer_files:
        w = f"a/{path.name}"
        aid = a.get("id", "")
        seen[aid] += 1
        nonblank(w, a, "content")
        nonblank(w, a, "style")
        author_ok(w, a)
        src = a.get("source")
        if not isinstance(src, dict) or not str(src.get("note", "")).strip():
            err(w, "缺 source.note（答案要写明出处或注明原创）")
        qid, cid = a.get("question_id"), a.get("canonical_id")
        if qid not in con.questions_by_id:
            err(w, f"指向不存在的问题 {qid}")
        canon = con.canonicals_by_id.get(cid)
        if not canon:
            err(w, f"指向不存在的正确答案 {cid}")
        elif canon.get("question_id") != qid:
            err(w, f"正确答案 {cid} 属于问题 {canon.get('question_id')}，与声明的 {qid} 不符")
        else:
            required = {i["id"] for i in canon.get("invariants", [])}
            missed = required - set(a.get("covers", []))
            if missed:
                err(w, f"同义改写漏掉要点 {sorted(missed)}，意思已经不一致")
    for aid, n in seen.items():
        if n > 1:
            err(f"a/{aid}", f"答案 id 重复 {n} 次")

    # 同一题内不许逐字复制
    for q in con.questions:
        texts = [a["content"].strip() for a in con.answers_of(q["id"])]
        dup = [t for t, n in Counter(texts).items() if n > 1]
        for t in dup:
            err(f"q/{q['id']}", "同一题内有逐字相同的答案，那是复制不是改写")


def check_coverage(c: Corpus, con):
    for q in con.questions:
        cans = con.canonicals_of(q["id"])
        canon = cans[0] if cans else None
        answers = con.answers_of(q["id"])
        if canon is None:
            warn(f"q/{q['id']}", "这道题还没有经审核认定的正确答案，属于待补格")
            continue
        if not answers:
            warn(f"q/{q['id']}", "已有正确答案但还没有任何同义改写")
        elif len(answers) < 2:
            warn(f"q/{q['id']}", "只有一条说法，建议再补一条不同表达，泛化训练才有意义")


def scan_garbage(c: Corpus):
    files = sorted((ROOT / "data").rglob("*.json")) + sorted((ROOT / "schema").rglob("*.json"))
    hits = 0
    for p in files:
        data = json.loads(p.read_text(encoding="utf-8"))
        for path, text in iter_strings(data):
            for h in find_garbage(text):
                err(f"garbage/{p.name}{path}", f"可疑片段「{h}」")
                hits += 1
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concept", default="", help="只检查某个概念，默认全部")
    args = ap.parse_args()

    c = Corpus()
    check_axes(c)
    if not c.concepts:
        err("concepts", "一个概念都没有")

    for con in c.concepts:
        if args.concept and con.id != args.concept:
            continue
        check_concept(c, con)
        check_questions(c, con)
        check_canonicals(c, con)
        check_answers(c, con)
        check_coverage(c, con)

    hits = scan_garbage(c)

    nq = sum(len(con.questions) for con in c.concepts)
    nc = sum(len(con.canonicals) for con in c.concepts)
    na = sum(len(con.answers) for con in c.concepts)
    print(f"\n=== 质检报告：{args.concept or '全部概念'} ===")
    print(f"  概念 {len(c.concepts)} / 问题 {nq} / 正确答案 {nc} / 同义改写 {na}")
    print(f"  errors   : {len(errors)}")
    print(f"  warnings : {len(warnings)}")
    print(f"  乱码可疑片段 : {hits}")
    for e in errors:
        print("  ERROR  " + e)
    for w in warnings:
        print("  WARN   " + w)
    if errors:
        print("\n未通过，请按上面的 ERROR 修正后再提交。")
        return 1
    print("\n质检通过，可以提交。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
