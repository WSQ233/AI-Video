#!/usr/bin/env python3
"""
在 Colab 确认所有节点与工作流稳定运行后，运行本脚本导出精确的 git commit SHA，
用于更新 configs/nodes_lock.json，确保以后每次重装环境 100% 一致不炸依赖。
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git_head(repo_dir: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_dir), text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="冻结当前稳定的 ComfyUI 与节点版本到 nodes_lock.json")
    parser.add_argument("--comfy-dir", default="/content/ComfyUI")
    parser.add_argument("--lock-file", default="configs/nodes_lock.json")
    parser.add_argument("--out", default=None, help="输出路径（默认覆盖 --lock-file）")
    args = parser.parse_args()

    comfy_dir = Path(args.comfy_dir)
    lock_path = Path(args.lock_file)
    data = json.loads(lock_path.read_text(encoding="utf-8"))

    if (comfy_dir / ".git").exists():
        data["comfyui"]["commit"] = git_head(comfy_dir)

    for node in data["custom_nodes"]:
        ndir = comfy_dir / "custom_nodes" / node["name"]
        if (ndir / ".git").exists():
            node["commit"] = git_head(ndir)

    out_path = Path(args.out) if args.out else lock_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[已锁定版本] 写入 {out_path}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
