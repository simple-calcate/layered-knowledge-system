#!/usr/bin/env python3
"""push_via_api.py — 当 git 的 https 通道连不上 github.com 时，用 REST API 完成推送。

为什么需要这个工具：
    `git push` 走的是 git-over-https，访问的是 github.com 域。
    某些网络环境下 github.com 被阻断，但 api.github.com 可达。
    GitHub 的 Git Data API 允许直接创建 blob → tree → commit → ref，
    效果与一次 push 等价，只是传输通道换成了 REST。

用法：
    python3 tools/push_via_api.py -m "提交说明"

行为：
    - 提交范围 = `git ls-files`（即已被 git 跟踪的文件），自动遵守 .gitignore
    - 目标仓库与分支从当前 git remote / 分支推断，可用 --owner/--repo/--branch 覆盖
    - 认证用 `gh auth token`，所以前提是先 `gh auth login`
    - 若远端仓库为空，会先种一个占位提交（Git Data API 不接受空仓库），
      再把分支强制指向真正的提交，因此最终 main 的历史里只有你这一次提交

注意：
    本脚本只处理文本文件；仓库里若含二进制大文件，请改用正规 git 通道。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def gh_token() -> str:
    return subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", required=True, help="提交说明")
    ap.add_argument("--owner", default="")
    ap.add_argument("--repo", default="")
    ap.add_argument("--branch", default="")
    args = ap.parse_args()

    token = gh_token()
    branch = args.branch or git("rev-parse", "--abbrev-ref", "HEAD")

    origin = git("remote", "get-url", "origin") if not (args.owner and args.repo) else ""
    if args.owner and args.repo:
        owner, repo = args.owner, args.repo
    else:
        # origin 形如 https://github.com/owner/repo.git 或 git@github.com:owner/repo.git
        tail = origin.replace("git@github.com:", "").replace("https://github.com/", "")
        tail = tail.rstrip("/").removesuffix(".git")
        owner, repo = tail.split("/")[-2:]

    api = f"https://api.github.com/repos/{owner}/{repo}"

    def req(method: str, url: str, payload: dict | None = None):
        data = json.dumps(payload).encode() if payload is not None else None
        r = urllib.request.Request(url, data=data, method=method)
        r.add_header("Authorization", f"Bearer {token}")
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} {method} {url}\n{e.read().decode()[:2000]}", file=sys.stderr)
            raise

    print(f"目标 {owner}/{repo}@{branch}")

    # 空仓库不接受 Git Data API，先用 Contents API 种一个占位提交
    try:
        req("POST", f"{api}/git/blobs", {"content": "init", "encoding": "utf-8"})
    except urllib.error.HTTPError as e:
        if e.code != 409:
            raise
        print("远端为空，先种占位提交 …")
        req("PUT", f"{api}/contents/.init", {
            "message": "chore: init",
            "content": base64.b64encode(b"init\n").decode(),
        })

    files = [f for f in git("ls-files").splitlines() if (ROOT / f).is_file()]
    print(f"待提交 {len(files)} 个文件")

    tree = []
    for i, rel in enumerate(files, 1):
        raw = (ROOT / rel).read_bytes()
        mode = "100755" if os.access(ROOT / rel, os.X_OK) else "100644"
        blob = req("POST", f"{api}/git/blobs", {
            "content": base64.b64encode(raw).decode(),
            "encoding": "base64",
        })
        tree.append({"path": rel, "mode": mode, "type": "blob", "sha": blob["sha"]})
        if i % 20 == 0 or i == len(files):
            print(f"  blob {i}/{len(files)}")

    tree_obj = req("POST", f"{api}/git/trees", {"tree": tree})
    commit = req("POST", f"{api}/git/commits", {"message": args.message, "tree": tree_obj["sha"]})
    print("commit", commit["sha"][:7])

    try:
        req("POST", f"{api}/git/refs", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
    except urllib.error.HTTPError:
        req("PATCH", f"{api}/git/refs/heads/{branch}", {"sha": commit["sha"], "force": True})

    print("完成 →", f"https://github.com/{owner}/{repo}/tree/{branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
