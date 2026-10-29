"""repair.py — 修复手写 LaTeX 在 JSON 里未转义的反斜杠。

问题：JSON 字符串中 `\\alpha` 才是字面量 `\alpha`；
写成单斜杠的 `\ell`、`\end` 等会被当成非法转义，导致 json.load 直接报错。

做法：逐字符扫描，遇到「单个反斜杠 + 非法转义字符」就补一个反斜杠；
已经正确的 `\\`、`\\"`、`\\n` 等保持原样。

用法: python3 pipeline/repair.py <file> [<file> ...]
"""

from __future__ import annotations

import sys
from pathlib import Path

VALID = set('"\\/bfnrtu')


def repair_line(line: str) -> str:
    out = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        nxt = line[i + 1] if i + 1 < n else ""
        if nxt in VALID:
            out.append(ch)
            out.append(nxt)
            i += 2
            continue
        # 非法转义：补一个反斜杠
        out.append("\\")
        out.append("\\")
        out.append(nxt)
        i += 2
    return "".join(out)


def main() -> int:
    for arg in sys.argv[1:]:
        p = Path(arg)
        before = p.read_text(encoding="utf-8")
        after = "\n".join(repair_line(l) for l in before.split("\n"))
        if after == before:
            print(f"无需修改 {p}")
            continue
        p.write_text(after, encoding="utf-8")
        print(f"已修复   {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
