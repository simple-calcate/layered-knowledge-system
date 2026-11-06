#!/usr/bin/env python3
"""push_via_api.py — 当 git 的 https 通道连不上 github.com 时，用 REST API 完成推送。

为什么需要这个工具：
    `git push` 走的是 git-over-https，访问 github.com 域。
    某些网络环境下 github.com 被阻断，但 api.github.com 可达。
    GitHub 的 Git Data API 允许直接创建 tree（文件正文内嵌）→ commit → ref，
    效果与一次 push 等价，只是传输通道换成了 REST。

两种模式（自动选择）：
    1. main 未受保护（或用 --direct）：建好 commit 后快进更新 main
    2. main 受分支保护：建临时分支 → 开 PR → 合并 → 删除临时分支
       这样审核规则有载体，CI 也会在 PR 上跑一遍

与早期版本的两个关键差别：
    - commit 带 parent（远端 main 的当前 HEAD），历史是累积的；
      早期版本每次都建 root commit 再 force 覆盖，远端历史永远只有一条
    - tree 内嵌文件正文，一次请求建完整棵树；逐个 POST /git/blobs 在
      跨境网络下极易 5xx / 超时

用法：
    python3 tools/push_via_api.py -m "提交说明"
    python3 tools/push_via_api.py -m "应急直推" --direct   # 跳过 PR

行为：
    - 提交范围 = `git ls-files`（已被 git 跟踪的文件），自动遵守 .gitignore
    - 目标仓库与分支从当前 git remote / 分支推断，可用 --owner/--repo/--branch 覆盖
    - 认证用 `gh auth token`，所以前提是先 `gh auth login`
    - 若远端仓库为空，先用 Contents API 种一个占位提交（Git Data API 不接受空仓库）

注意：
    - 本脚本只处理文本文件；仓库里若含二进制大文件，请改用正规 git 通道
    - 本地 main 只是「文件来源」：commit 由 API 创建，SHA 与本地 git commit 不同。
      脚本每次都从远端 HEAD 取 parent，所以这不影响正确性
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ApiError(Exception):
    def __init__(self, code: int, body: str, method: str, url: str):
        super().__init__(f"HTTP {code} {method} {url}\n{body[:2000]}")
        self.code = code
        self.body = body
        self.method = method
        self.url = url


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def gh_token() -> str:
    return subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()


class GitHub:
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base = f"https://api.github.com/repos/{owner}/{repo}"

    def req(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        *,
        quiet: tuple[int, ...] = (),
        _attempt: int = 1,
    ) -> dict:
        url = path if path.startswith("http") else self.base + path
        data = (
            json.dumps(payload, ensure_ascii=False).encode("utf-8")
            if payload is not None
            else None
        )
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", f"Bearer {self.token}")
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            # GitHub 偶发 5xx / 限流；这些写操作是幂等的，安全重试
            if (500 <= e.code < 600 or e.code == 429) and _attempt < 4:
                wait = 2**_attempt
                print(f"  {e.code}，{wait}s 后重试（第 {_attempt} 次）", file=sys.stderr)
                time.sleep(wait)
                return self.req(method, path, payload, quiet=quiet, _attempt=_attempt + 1)
            if e.code not in quiet:
                print(f"HTTP {e.code} {method} {url}\n{body[:2000]}", file=sys.stderr)
            raise ApiError(e.code, body, method, url)
        except urllib.error.URLError as e:
            if _attempt < 4:
                wait = 2**_attempt
                print(f"  网络超时（{e.reason}），{wait}s 后重试（第 {_attempt} 次）", file=sys.stderr)
                time.sleep(wait)
                return self.req(method, path, payload, quiet=quiet, _attempt=_attempt + 1)
            raise


def is_protected(gh: GitHub, branch: str) -> bool:
    """404 = 未保护；其余错误照常抛出，避免把权限问题误判成「可以直接推」。"""
    try:
        gh.req("GET", f"/branches/{branch}/protection", quiet=(404,))
        return True
    except ApiError as e:
        if e.code == 404:
            return False
        raise


def merge_via_pr(gh: GitHub, branch: str, sha: str, message: str) -> int:
    """临时分支 → PR → 合并 → 删分支。受保护分支下唯一合规的推送路径。"""
    tmp = f"bot-{time.strftime('%Y%m%d%H%M%S')}-{sha[:7]}"
    title = message.splitlines()[0][:120]

    gh.req("POST", "/git/refs", {"ref": f"refs/heads/{tmp}", "sha": sha})
    print(f"临时分支 {tmp}")

    pr = gh.req("POST", "/pulls", {
        "title": title,
        "head": tmp,
        "base": branch,
        "body": (
            "由 `tools/push_via_api.py` 自动创建 —— 本机无法直连 github.com，改走 REST。\n\n"
            + message
        ),
    })
    num = pr["number"]
    print(f"PR #{num} → {pr['html_url']}")

    # GitHub 需要一点时间计算 mergeable；None 表示还没算完
    for _ in range(15):
        state = gh.req("GET", f"/pulls/{num}")
        if state.get("mergeable") is True:
            break
        if state.get("mergeable") is False:
            print("PR 与目标分支冲突，保留临时分支供人工处理", file=sys.stderr)
            return 1
        time.sleep(2)

    try:
        merged = gh.req("PUT", f"/pulls/{num}/merge", {
            "commit_title": title,
            "commit_message": message,
            "merge_method": "merge",
            "sha": sha,
        })
    except ApiError:
        print("合并被保护规则挡下（多半在等 code owner 批准）。", file=sys.stderr)
        print(f"请到 {pr['html_url']} 完成审核后合并，并手动删除分支 {tmp}。", file=sys.stderr)
        return 1

    print("已合并", merged.get("sha", "")[:7])
    try:
        gh.req("DELETE", f"/git/refs/heads/{tmp}")
        print("临时分支已清理")
    except ApiError as e:
        print(f"临时分支清理失败（可手动删）：{e}", file=sys.stderr)

    print("完成 →", f"https://github.com/{gh.owner}/{gh.repo}/tree/{branch}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", required=True, help="提交说明")
    ap.add_argument("--owner", default="")
    ap.add_argument("--repo", default="")
    ap.add_argument("--branch", default="")
    ap.add_argument("--direct", action="store_true", help="跳过 PR，直接更新分支（应急）")
    args = ap.parse_args()

    branch = args.branch or git("rev-parse", "--abbrev-ref", "HEAD")
    if args.owner and args.repo:
        owner, repo = args.owner, args.repo
    else:
        origin = git("remote", "get-url", "origin")
        tail = origin.replace("git@github.com:", "").replace("https://github.com/", "")
        tail = tail.rstrip("/").removesuffix(".git")
        owner, repo = tail.split("/")[-2:]

    gh = GitHub(gh_token(), owner, repo)
    print(f"目标 {owner}/{repo}@{branch}")

    # 远端 HEAD 既用来判断空仓库，也是新 commit 的 parent
    try:
        head = gh.req("GET", f"/git/ref/heads/{branch}", quiet=(404,))["object"]["sha"]
    except ApiError as e:
        if e.code != 404:
            raise
        print("远端为空，先种占位提交 …")
        gh.req("PUT", "/contents/.init", {
            "message": "chore: init",
            "content": base64.b64encode(b"init\n").decode(),
        })
        head = gh.req("GET", f"/git/ref/heads/{branch}")["object"]["sha"]

    files = [f for f in git("ls-files").splitlines() if (ROOT / f).is_file()]
    print(f"待提交 {len(files)} 个文件，parent {head[:7]}")

    # tree 接口允许直接带 content，GitHub 会自己写出 blob。
    # 一次请求搞定全部文件，比逐个 POST /git/blobs 稳得多（跨境网络尤其明显）。
    tree = []
    for rel in files:
        raw = (ROOT / rel).read_bytes()
        mode = "100755" if os.access(ROOT / rel, os.X_OK) else "100644"
        tree.append({
            "path": rel,
            "mode": mode,
            "type": "blob",
            "content": raw.decode("utf-8"),
        })
    print(f"建树（{len(tree)} 个文件，单次请求）…")
    tree_obj = gh.req("POST", "/git/trees", {"tree": tree})
    commit = gh.req("POST", "/git/commits", {
        "message": args.message,
        "tree": tree_obj["sha"],
        "parents": [head],
    })
    sha = commit["sha"]
    print("commit", sha[:7])

    protected = is_protected(gh, branch)
    if protected and not args.direct:
        print("检测到分支保护 → 走 PR 流程")
        return merge_via_pr(gh, branch, sha, args.message)

    # 快进更新即可，不再需要 force —— 因为新 commit 本来就是 head 的直接后代
    gh.req("PATCH", f"/git/refs/heads/{branch}", {"sha": sha, "force": False})
    print("完成 →", f"https://github.com/{gh.owner}/{gh.repo}/tree/{branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
