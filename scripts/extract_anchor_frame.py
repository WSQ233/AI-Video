#!/usr/bin/env python3
"""
美术定妆立锚与跨镜尾帧接力抽帧工具 (art-director & film-editor 专用脚本)：
1. 定妆立锚模式 (--timestamp)：从首镜或定妆视频的指定秒数无损截取高清 PNG 帧，
   自动归档至 characters/<character_id>/ref_<character_id>.png、outfits/ 或 images/scenes/<scene_id>/。
2. 突破 H3 15 秒上限的尾帧接力模式 (--last-frame)：无损提取上一镜视频的最后一帧，
   自动存入 images/keyframes/<shot_id>_tail.png 与 outputs/extracted_frames/，供下一镜 I2V 作为 first_frame 无缝接力。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def probe_duration(video_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def extract_frame_ffmpeg(video_path: Path, output_png: Path, timestamp: float | None, last_frame: bool) -> None:
    output_png.parent.mkdir(parents=True, exist_ok=True)
    if last_frame:
        # 使用 -sseof -0.05 提取视频末尾最后一帧
        cmd = [
            "ffmpeg", "-y",
            "-sseof", "-0.05",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "1",
            str(output_png),
        ]
    else:
        ts = max(0.0, float(timestamp or 0.0))
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{ts:.3f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "1",
            str(output_png),
        ]
    subprocess.run(cmd, check=True)
    if not output_png.is_file() or output_png.stat().st_size == 0:
        raise RuntimeError(f"抽帧失败，未生成有效 PNG 文件: {output_png}")


def main() -> int:
    parser = argparse.ArgumentParser(description="从生成视频中抽取人物/场景定妆锚点帧或跨镜接力尾帧")
    parser.add_argument("--project-dir", required=True, help="剧本项目目录路径（如 projects/01_rainy_signal 或云盘对应路径）")
    parser.add_argument("--video", required=True, help="源视频 .mp4 路径")
    parser.add_argument("--timestamp", type=float, default=2.0, help="定妆抽帧时间点（秒，默认 2.0s）")
    parser.add_argument("--last-frame", action="store_true", help="提取视频最后一帧（用于突破 H3 15 秒上限的跨镜尾帧接力）")
    parser.add_argument("--character", default=None, help="自动归档为指定人物 ID 的主锚定图 (characters/<id>/ref_<id>.png)")
    parser.add_argument("--outfit", default=None, help="可选：同时归档为该人物的指定造型图 (characters/<id>/outfits/<outfit>.png)")
    parser.add_argument("--scene", default=None, help="可选：归档为指定场次的环境基准图 (images/scenes/<scene_id>/env_master.png)")
    parser.add_argument("--keyframe-name", default=None, help="可选：归档至 images/keyframes/<name>.png（供下一镜 first_frame/last_frame 使用）")
    parser.add_argument("--out", default=None, help="可选：自定义输出 PNG 绝对/相对路径")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    video_path = Path(args.video).resolve()
    if not video_path.is_file():
        print(f"[错误] 找不到源视频文件: {video_path}", file=sys.stderr)
        return 1

    extracted_dir = project_dir / "outputs" / "extracted_frames"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    tag = "tail" if args.last_frame else f"t{str(args.timestamp).replace('.', '_')}s"
    archive_png = extracted_dir / f"{video_path.stem}_{tag}.png"

    extract_frame_ffmpeg(video_path, archive_png, args.timestamp, args.last_frame)
    targets: list[Path] = [archive_png]

    if args.character:
        cid = args.character.strip()
        char_primary = project_dir / "characters" / cid / f"ref_{cid}.png"
        char_primary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive_png, char_primary)
        targets.append(char_primary)
        if args.outfit:
            outfit_name = args.outfit.strip().removesuffix(".png")
            outfit_png = project_dir / "characters" / cid / "outfits" / f"{outfit_name}.png"
            outfit_png.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(archive_png, outfit_png)
            targets.append(outfit_png)

    if args.scene:
        sid = args.scene.strip()
        scene_png = project_dir / "images" / "scenes" / sid / "env_master.png"
        scene_png.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive_png, scene_png)
        targets.append(scene_png)

    if args.keyframe_name or args.last_frame:
        kf_stem = (args.keyframe_name or f"{video_path.stem}_tail").strip().removesuffix(".png")
        kf_png = project_dir / "images" / "keyframes" / f"{kf_stem}.png"
        kf_png.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive_png, kf_png)
        targets.append(kf_png)

    if args.out:
        custom_out = Path(args.out)
        if not custom_out.is_absolute():
            custom_out = project_dir / custom_out
        custom_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archive_png, custom_out)
        targets.append(custom_out)

    print(f"[抽帧成功] 源视频: {video_path.name} ({'尾帧接力模式' if args.last_frame else f'{args.timestamp}s 定妆模式'})")
    for t in targets:
        print(f"  -> {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
