#!/usr/bin/env python3
"""
原视频下载与 H3 <=15 秒 (17k+5 帧网格) 分镜切片预处理工具：
用于「原视频 + 参考图直出 (Ref2VA Video + Image)」模式：
1. 在 Colab 免费 CPU 运行时（0 CU）或本地通过 yt-dlp 下载 project.json 中配置的 source_video_url
   至项目云端目录 videos/raw_source.mp4（或直接指定已下载的 --source-video）。
2. 读取项目 tasks.csv 中的 video、source_start_sec、frames、fps、width、height 列，
   严格按 MiniMax H3 24fps 下 17k+5 帧数网格（单镜 <= 15.0s）调用 ffmpeg 精确切片为
   videos/source_clips/<task_id>_src.mp4（供 VHS_LoadVideo 作为 <Video 1> 输入）。
3. 自动同步抽取每个原视频切片的首帧至 images/keyframes/<task_id>_src_first.png 便于预览与校验。
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def download_youtube_video(url: str, dest_mp4: Path) -> None:
    dest_mp4.parent.mkdir(parents=True, exist_ok=True)
    if dest_mp4.is_file() and dest_mp4.stat().st_size > 0:
        print(f"[跳过下载] 原视频已存在: {dest_mp4}")
        return
    tmp_mp4 = dest_mp4.with_suffix(".part.mp4")
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(tmp_mp4),
        url,
    ]
    print(f"[下载原视频] $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    if not tmp_mp4.is_file():
        raise RuntimeError(f"yt-dlp 下载未生成预期文件: {tmp_mp4}")
    tmp_mp4.replace(dest_mp4)
    print(f"[下载完成] 原视频已保存至: {dest_mp4}")


def slice_one_clip(
    source_mp4: Path,
    dest_clip: Path,
    start_sec: float,
    frames: int,
    fps: int,
    width: int,
    height: int,
    keyframe_png: Path | None = None,
) -> None:
    dest_clip.parent.mkdir(parents=True, exist_ok=True)
    duration = frames / fps
    vf = (
        f"fps={fps},"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_sec:.3f}",
        "-i", str(source_mp4),
        "-t", f"{duration:.3f}",
        "-vf", vf,
        "-frames:v", str(frames),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-ar", "32000",
        "-ac", "2",
        str(dest_clip),
    ]
    subprocess.run(cmd, check=True)

    if keyframe_png:
        keyframe_png.parent.mkdir(parents=True, exist_ok=True)
        kf_cmd = [
            "ffmpeg", "-y",
            "-i", str(dest_clip),
            "-frames:v", "1",
            "-q:v", "1",
            str(keyframe_png),
        ]
        subprocess.run(kf_cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="下载原视频并按 tasks.csv 的 17k+5 (<=15s) 分镜时间轴切片供 Ref2VA 直出")
    parser.add_argument("--project-dir", required=True, help="剧本项目目录路径（如 projects/02_yongzheng_ep12_huang）")
    parser.add_argument("--source-url", default=None, help="可选：覆盖 project.json 中的 source_video_url")
    parser.add_argument("--source-video", default=None, help="可选：本地/云盘已有的原视频文件路径（默认 videos/raw_source.mp4）")
    parser.add_argument("--skip-download", action="store_true", help="跳过 yt-dlp 下载，直接使用已有原视频切片")
    parser.add_argument("--dry-run", action="store_true", help="仅打印分镜切片计划，不执行下载与 ffmpeg")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    meta_path = project_dir / "project.json"
    tasks_path = project_dir / "tasks.csv"
    if not meta_path.is_file() or not tasks_path.is_file():
        print(f"[错误] 缺少 project.json 或 tasks.csv: {project_dir}", file=sys.stderr)
        return 1

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    source_url = args.source_url or meta.get("source_video_url", "")
    raw_source = Path(args.source_video).resolve() if args.source_video else (project_dir / "videos" / "raw_source.mp4")

    with tasks_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    print(f"[原视频预处理] 项目: {project_dir.name} | 原视频 URL: {source_url or 'N/A'}")
    print(f"  - 原视频落地路径: {raw_source}")
    print(f"  - 分镜切片总数  : {len(rows)}")

    if args.dry_run:
        for idx, row in enumerate(rows, start=1):
            tid = (row.get("task_id") or f"shot_{idx:02d}").strip()
            vrel = (row.get("video") or f"videos/source_clips/{tid}_src.mp4").strip()
            start_s = float(row.get("source_start_sec") or 0.0)
            frames = int(row.get("frames") or 124)
            fps = int(row.get("fps") or 24)
            print(f"  [{idx}/{len(rows)}] {tid}: start={start_s:.2f}s, frames={frames} ({frames/fps:.2f}s) -> {vrel}")
        return 0

    if not args.skip_download and source_url and not raw_source.is_file():
        download_youtube_video(source_url, raw_source)

    if not raw_source.is_file():
        print(f"[错误] 未找到原视频文件: {raw_source}", file=sys.stderr)
        return 1

    for idx, row in enumerate(rows, start=1):
        tid = (row.get("task_id") or f"shot_{idx:02d}").strip()
        vrel = (row.get("video") or "").strip()
        if not vrel:
            continue
        start_s = float(row.get("source_start_sec") or 0.0)
        frames = int(row.get("frames") or 124)
        fps = int(row.get("fps") or 24)
        width = int(row.get("width") or 1344)
        height = int(row.get("height") or 768)
        dest_clip = project_dir / vrel
        kf_png = project_dir / "images" / "keyframes" / f"{tid}_src_first.png"
        print(f"[{idx}/{len(rows)}] 正在切片 {tid}: {start_s:.2f}s 起 {frames} 帧 ({frames/fps:.2f}s) -> {dest_clip}")
        slice_one_clip(raw_source, dest_clip, start_s, frames, fps, width, height, keyframe_png=kf_png)

    print("[完成] 所有原视频 <=15s 分镜切片与首帧已就绪！")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
