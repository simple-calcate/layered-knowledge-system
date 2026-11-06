"""garbage_scan.py — 扫描数据文件中的注入/乱码片段。

判据（强信号）：西文/西里尔字母串与汉字直接相邻且无空格。
正常书写中，英文单词与汉字之间一定留空格，所以这种粘连几乎必然是注入内容。

用法: python3 pipeline/garbage_scan.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CJK = r"\u4e00-\u9fff"
# 非 ASCII 的其它字母（西里尔、拉丁扩展等）
OTHER_LETTER = r"\u0100-\u024f\u0370-\u03ff\u0400-\u04ff\u00c0-\u00ff"

ADJACENT = re.compile(
    rf"([{CJK}][A-Za-z{OTHER_LETTER}]{{3,}}|[{OTHER_LETTER}A-Za-z]{{3,}}[{CJK}])"
)
CYRILLIC = re.compile(r"[\u0400-\u04ff]{3,}")

CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")


def clean(text: str) -> str:
    return INLINE_CODE.sub(" ", CODE_FENCE.sub(" ", text))


def walk(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def main() -> int:
    files = sorted(ROOT.glob("data/**/*.json")) + sorted(ROOT.glob("schema/*.json"))
    total = 0
    for fp in files:
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[!] JSON 解析失败 {fp.name}: {e}")
            continue
        for path, text in walk(doc):
            t = clean(text)
            hits = set(ADJACENT.findall(t)) | set(CYRILLIC.findall(t))
            hits = {h for h in hits if len(h.strip()) > 3}
            if hits:
                rel = fp.relative_to(ROOT)
                print(f"\n== {rel}  {path}")
                for h in sorted(hits):
                    print(f"   {h!r}")
                total += len(hits)
    print(f"\n合计可疑片段 {total} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
