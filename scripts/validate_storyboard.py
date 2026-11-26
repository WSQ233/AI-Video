#!/usr/bin/env python3
"""
剧本项目细粒度资产结构与分镜头剧本 (MiniMax H3 15 秒上限 & 17k+5 时间网格) 完整性校验器。
由项目级 `screenwriter`、`art-director`、`director`、`film-editor` 技能在产出或修改分镜头剧本后自动调用：
1. 校验剧本项目目录下具备完整资产结构：原始剧本 (source_script.md)、分镜头剧本 (storyboard.md)、
   任务表 (tasks.csv)、细粒度图片资源 (images/scenes/, images/props/, images/keyframes/)、
   人物独立形象目录 (characters/<character_id>/ 及其 outfits/ 与 voice/)、
   全局音频目录 (audio/)、产出视频四层目录 (outputs/) 与项目专属 ComfyUI 流程 (workflows/*.json)。
2. 校验所有分镜严格遵守 MiniMax H3 的 15 秒单镜物理上限（duration = frames / fps <= 15.0s）
   以及 24fps 下 17k + 5 帧数网格（如 56, 90, 124, 158, 192, 243, 294, 345 帧）。
3. 校验多模态工作流绑定（单图 Ref2VA、双图 Ref2VA Multi `<Picture 1>` + `<Picture 2>`、首尾帧 Bridge）。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


REQUIRED_PROJECT_FILES = (
    "project.json",
    "source_script.md",
    "storyboard.md",
    "tasks.csv",
)

REQUIRED_PROJECT_DIRS = (
    "images",
    "images/scenes",
    "images/props",
    "images/keyframes",
    "characters",
    "audio",
    "workflows",
    "outputs",
    "logs",
)

REQUIRED_CSV_COLUMNS = (
    "task_id",
    "workflow",
    "prompt",
    "negative_prompt",
    "image",
    "seed",
    "width",
    "height",
    "frames",
    "fps",
)


def validate_one_project(project_dir: Path, max_seconds: float = 15.0) -> list[str]:
    errors: list[str] = []
    pid = project_dir.name

    for req_file in REQUIRED_PROJECT_FILES:
        if not (project_dir / req_file).is_file():
            errors.append(f"[{pid}] 缺少必需项目文件: {req_file}")

    for req_dir in REQUIRED_PROJECT_DIRS:
        if not (project_dir / req_dir).is_dir():
            errors.append(f"[{pid}] 缺少必需项目子目录: {req_dir}/")

    if errors:
        return errors

    # 1. 校验 project.json、人物独立文件夹（含 outfits/ 与 voice/）与场次空间锚点文件夹
    try:
        meta = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"[{pid}] project.json 解析失败: {exc}")
        meta = {}

    chars_root = project_dir / "characters"
    char_folders = [p for p in chars_root.iterdir() if p.is_dir()]
    if not char_folders:
        errors.append(f"[{pid}] characters/ 下至少应包含 1 个独立人物文件夹 (如 characters/<character_id>/)")

    for cdir in char_folders:
        cjson = cdir / "character.json"
        if not cjson.is_file():
            errors.append(f"[{pid}] 人物独立文件夹缺少设定卡: characters/{cdir.name}/character.json")
        else:
            try:
                cdata = json.loads(cjson.read_text(encoding="utf-8"))
                if not cdata.get("visual_anchor_en"):
                    errors.append(f"[{pid}] characters/{cdir.name}/character.json 缺少 visual_anchor_en 字段")
            except Exception as exc:
                errors.append(f"[{pid}] characters/{cdir.name}/character.json 解析失败: {exc}")
        for sub in ("outfits", "voice"):
            if not (cdir / sub).is_dir():
                errors.append(f"[{pid}] 人物独立文件夹 characters/{cdir.name}/ 缺少 {sub}/ 子目录")

    for cmeta in meta.get("characters", []):
        cid = cmeta.get("character_id", "")
        if cid and not (chars_root / cid).is_dir():
            errors.append(f"[{pid}] project.json 声明的角色 '{cid}' 未在 characters/{cid}/ 建立独立文件夹")

    scenes_root = project_dir / "images" / "scenes"
    for smeta in meta.get("scenes", []):
        sid = smeta.get("scene_id", "")
        if sid:
            sjson = scenes_root / sid / "scene.json"
            if not sjson.is_file():
                errors.append(f"[{pid}] project.json 声明的场次 '{sid}' 缺少空间锚点设定卡: images/scenes/{sid}/scene.json")

    # 2. 校验 workflows/ 下是否存储了本项目的 ComfyUI 流程 JSON
    wf_dir = project_dir / "workflows"
    wf_files = list(wf_dir.glob("*.json"))
    if not wf_files:
        errors.append(f"[{pid}] workflows/ 目录下未存储任何 ComfyUI 流程 JSON 文件")

    # 3. 校验 tasks.csv 分镜参数与 H3 15 秒限制
    tasks_path = project_dir / "tasks.csv"
    with tasks_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for col in REQUIRED_CSV_COLUMNS:
            if col not in fieldnames:
                errors.append(f"[{pid}] tasks.csv 缺少必需列: {col}")
        rows = list(reader)

    if not rows:
        errors.append(f"[{pid}] tasks.csv 不能为空，至少应包含 1 条分镜记录")

    seen_ids: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        tid = (row.get("task_id") or "").strip()
        if not tid:
            errors.append(f"[{pid}] tasks.csv 第 {idx} 行缺少 task_id")
            continue
        if tid in seen_ids:
            errors.append(f"[{pid}] tasks.csv 存在重复 task_id: {tid}")
        seen_ids.add(tid)

        wf_name = (row.get("workflow") or "").strip()
        if not wf_name or not (wf_dir / wf_name).is_file():
            errors.append(f"[{pid}] 分镜 {tid} 引用的工作流 '{wf_name}' 未存储在本项目 workflows/ 目录下")

        try:
            width = int(row.get("width") or 0)
            height = int(row.get("height") or 0)
            frames = int(row.get("frames") or 0)
            fps = int(row.get("fps") or 0)
        except ValueError:
            errors.append(f"[{pid}] 分镜 {tid} 的 width/height/frames/fps 必须为整数")
            continue

        if width <= 0 or height <= 0 or width % 32 != 0 or height % 32 != 0:
            errors.append(f"[{pid}] 分镜 {tid} 分辨率 {width}x{height} 违反 H3 32 倍数约束")

        if fps <= 0:
            errors.append(f"[{pid}] 分镜 {tid} 的 fps ({fps}) 必须大于 0")
            continue

        duration = frames / fps
        if duration > max_seconds:
            errors.append(
                f"[{pid}] 分镜 {tid} 时长 {duration:.2f}s ({frames}帧@{fps}fps) 超过 MiniMax H3 单镜 {max_seconds:.1f}s 上限！请拆分为多个分镜或使用尾帧接力。"
            )

        if frames < 5 or (frames - 5) % 17 != 0:
            errors.append(
                f"[{pid}] 分镜 {tid} 帧数 {frames} 未对齐 MiniMax H3 的 17k+5 时间网格（推荐 56/90/124/158/192/243/294/345 帧）"
            )

        prompt = (row.get("prompt") or "").strip()
        image = (row.get("image") or "").strip()
        image_2 = (row.get("image_2") or "").strip()
        video = (row.get("video") or "").strip()
        if "Audio:" not in prompt:
            errors.append(f"[{pid}] 分镜 {tid} 的 prompt 缺少 'Audio:' 原生音轨描述段落")

        wf_lower = wf_name.lower()
        if "ref2va" in wf_lower:
            if not image:
                errors.append(f"[{pid}] Ref2VA 分镜 {tid} 必须在 image 列绑定人物形象锚定图 (如 characters/<id>/ref_<id>.png)")
            elif not (image.startswith("characters/") or image.startswith("images/")):
                errors.append(
                    f"[{pid}] 分镜 {tid} 的 image ('{image}') 应指向本项目 'characters/<character_id>/' 或 'images/' 目录"
                )
            if "<Picture 1>" not in prompt:
                errors.append(f"[{pid}] Ref2VA 分镜 {tid} 的 prompt 必须显式包含 '<Picture 1>' 引用第一参考图")
            if "multi" in wf_lower:
                if not image_2:
                    errors.append(f"[{pid}] 多图锚定分镜 {tid} ({wf_name}) 必须在 image_2 列提供第二参考图（如配角或 images/scenes/<sid>/env_master.png）")
                if "<Picture 2>" not in prompt:
                    errors.append(f"[{pid}] 多图锚定分镜 {tid} 的 prompt 必须显式包含 '<Picture 2>' 引用第二参考图")
            if "video" in wf_lower:
                if not video:
                    errors.append(f"[{pid}] 原视频+参考图直出分镜 {tid} ({wf_name}) 必须在 video 列提供原视频切片路径 (如 videos/source_clips/{tid}_src.mp4)")
                elif not video.startswith("videos/"):
                    errors.append(f"[{pid}] 分镜 {tid} 的 video ('{video}') 应指向本项目 'videos/' 目录")
                if "<Video 1>" not in prompt:
                    errors.append(f"[{pid}] 原视频+参考图直出分镜 {tid} 的 prompt 必须显式包含 '<Video 1>' 引用原视频片段")

        if "bridge" in wf_lower and (not image or not image_2):
            errors.append(f"[{pid}] 首尾帧过渡分镜 {tid} ({wf_name}) 必须同时提供 image (首帧) 与 image_2 (尾帧)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验剧本项目细粒度目录结构、人物/场景锚定资产与 H3 15秒分镜约束")
    parser.add_argument("--repo-root", default=".", help="AI-Video 仓库根目录")
    parser.add_argument("--project", default=None, help="指定校验的剧本项目 ID（不传则校验 projects/ 下全部项目）")
    parser.add_argument("--max-seconds", type=float, default=15.0, help="MiniMax H3 单镜头最大秒数上限（默认 15.0 秒）")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    projects_root = repo_root / "projects"
    if not projects_root.is_dir():
        print(f"[错误] 未找到 projects 目录: {projects_root}", file=sys.stderr)
        return 1

    if args.project:
        targets = [projects_root / args.project]
    else:
        targets = sorted(p for p in projects_root.iterdir() if p.is_dir())

    if not targets:
        print("[错误] 未找到任何剧本项目目录", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for pdir in targets:
        if not pdir.is_dir():
            all_errors.append(f"剧本项目目录不存在: {pdir}")
            continue
        errs = validate_one_project(pdir, max_seconds=args.max_seconds)
        if errs:
            all_errors.extend(errs)
        else:
            print(f"[校验通过] 剧本项目 {pdir.name}: 细粒度资产目录、独立人物/场次锚点、专属 ComfyUI 流程与 H3 <=15s (17k+5) 分镜全部合规！")

    if all_errors:
        print("\n[校验失败] 发现以下问题：", file=sys.stderr)
        for e in all_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
