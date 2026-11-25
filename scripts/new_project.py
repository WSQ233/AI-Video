#!/usr/bin/env python3
"""
新建独立 AI 视频剧本项目的脚手架脚本。
用法: python scripts/new_project.py 02_cyber_chase "赛博追逐"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="创建新的独立剧本/短片项目目录")
    parser.add_argument("project_id", help="项目目录名，如 02_cyber_chase")
    parser.add_argument("title", help="项目中文/英文标题")
    parser.add_argument("--repo-root", default=".", help="仓库根目录")
    parser.add_argument("--drive-root", default="/content/drive/MyDrive/AI_Video", help="云盘根目录")
    args = parser.parse_args()

    pdir = Path(args.repo_root).resolve() / "projects" / args.project_id
    for sub in ("inputs", "workflows"):
        (pdir / sub).mkdir(parents=True, exist_ok=True)
        (pdir / sub / ".gitkeep").write_text(
            f"# {args.project_id}/{sub}（大文件存放在 5TB Google Drive）\n",
            encoding="utf-8",
        )

    meta = {
        "project_id": args.project_id,
        "title": args.title,
        "type": "short_film",
        "engine": "MiniMax-H3-33.1B-BF16",
        "active_packs": [
            "minimax_h3_fl2va_bf16",
            "minimax_h3_ref2va_bf16",
            "minimax_h3_turbo_lora",
        ],
        "resolution": "1280x720",
        "fps": 24,
        "cloud_dir": f"{args.drive_root}/projects/{args.project_id}",
    }
    (pdir / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pdir / "script.md").write_text(
        f"# 项目：{args.title} (`{args.project_id}`)\n\n"
        f"- **云端目录**：`{args.drive_root}/projects/{args.project_id}/`\n"
        f"- **引擎**：MiniMax H3 33.1B BF16\n\n"
        f"## 分镜 1\n- **画面 Prompt**：\n- **原生音频 Prompt**：\n",
        encoding="utf-8",
    )
    (pdir / "tasks.csv").write_text(
        "task_id,workflow,prompt,negative_prompt,image,seed,width,height,frames,fps\n"
        f"{args.project_id}_shot01,minimax_h3_fl2va_api.json,\"\",\"blurry, artifacts, watermark\",\"\",1001,1280,720,121,24\n",
        encoding="utf-8",
    )
    print(f"[已创建项目] {pdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
