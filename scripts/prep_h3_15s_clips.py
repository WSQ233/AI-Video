#!/usr/bin/env python3
"""
为 MiniMax H3 Ref2VA 15 秒原片编辑验证裁切干净的单镜参考视频与纯净角色参考音轨：
- 从项目 videos/raw_court_ep12.mp4 按精确镜头切点裁出 3 个 24fps 1280x704 单镜参考片段
- 对原片底部硬编码字幕条区域执行轻量级 delogo 柔化，配合 H3 Prompt 彻底消除画面字幕残留
- 切出对应角色的纯净中文声纹参考音轨（供 MiniMaxH3ReferenceToVideo <Audio 1> 绑定）
- 同步最新工作流 JSON 与 tasks_h3_15s_test.csv 到云端剧本项目目录
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def probe_video_size(path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True)
    stream = json.loads(out)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def run_ffmpeg(cmd: list[str]) -> None:
    print("[ffmpeg]", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="准备 02_yongzheng_ep12_huang 的 MiniMax H3 15 秒原片编辑验证素材")
    parser.add_argument(
        "--project-dir",
        default="/content/drive/MyDrive/AI_Video/projects/02_yongzheng_ep12_huang",
        help="云端剧本项目目录",
    )
    parser.add_argument(
        "--repo-root",
        default="/content/AI-Video",
        help="代码仓库根目录",
    )
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=544)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    repo_root = Path(args.repo_root)
    raw_video = project_dir / "videos" / "raw_court_ep12.mp4"
    if not raw_video.is_file():
        raise FileNotFoundError(f"找不到原片视频: {raw_video}")

    # 1. 同步最新工作流与 15s 测试任务表到项目目录
    repo_proj = repo_root / "projects" / "02_yongzheng_ep12_huang"
    wf_dst = project_dir / "workflows"
    wf_dst.mkdir(parents=True, exist_ok=True)
    for wf in (repo_proj / "workflows").glob("*.json"):
        shutil.copy2(wf, wf_dst / wf.name)
    for wf in (repo_root / "workflows" / "shared").glob("*.json"):
        shutil.copy2(wf, wf_dst / wf.name)
    shutil.copy2(repo_proj / "tasks_h3_15s_test.csv", project_dir / "tasks_h3_15s_test.csv")
    print("[同步] 已将最新工作流 JSON 与 tasks_h3_15s_test.csv 同步至云端项目目录")

    # 2. 按镜头切点裁切 3 段 24fps 1280x704 干净参考视频（对底部字幕带做轻量级 delogo）
    src_w, src_h = probe_video_size(raw_video)
    print(f"[探测] 原片分辨率: {src_w}x{src_h}")

    # 缩放填满 1280x704 后，底部字幕带大约位于 y=588..692 (x=80..1200)
    w, h = args.width, args.height
    dl_x = max(1, int(w * 0.06))
    dl_w = min(w - dl_x - 2, int(w * 0.88))
    dl_y = max(1, int(h * 0.84))
    dl_h = min(h - dl_y - 2, int(h * 0.14))
    vf = (
        f"fps={args.fps},"
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"delogo=x={dl_x}:y={dl_y}:w={dl_w}:h={dl_h}:show=0"
    )

    clips_dir = project_dir / "videos" / "source_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip_specs = [
        ("h3_15s_s01_kangxi.mp4", 0.00, 3.85),
        ("h3_15s_s02_maqi.mp4", 3.85, 2.40),
        ("h3_15s_s03_tongguowei.mp4", 5.75, 8.80),
    ]
    for name, start_sec, dur_sec in clip_specs:
        out_path = clips_dir / name
        run_ffmpeg([
            "ffmpeg", "-y",
            "-ss", f"{start_sec:.2f}",
            "-i", str(raw_video),
            "-t", f"{dur_sec:.2f}",
            "-vf", vf,
            "-an",
            "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
            str(out_path),
        ])

    # 3. 切出纯净角色中文声纹参考音轨（优先使用已验证清晰的 IndexTTS-2 中文音轨，兜底用原始参考干音）
    audio_dir = project_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    dubbed_v2 = project_dir / "outputs" / "replace_v2_preview" / "dubbed_master_audio_v2.wav"

    audio_specs = [
        ("h3_15s_s01_trump_voice.wav", 1.15, 2.75, project_dir / "characters" / "trump" / "voice" / "ref_trump.wav"),
        ("h3_15s_s03_rubio_voice.wav", 5.55, 8.35, project_dir / "characters" / "marco_rubio" / "voice" / "ref_marco_rubio.wav"),
    ]
    for out_name, start_sec, dur_sec, fallback_wav in audio_specs:
        out_wav = audio_dir / out_name
        if dubbed_v2.is_file():
            run_ffmpeg([
                "ffmpeg", "-y",
                "-ss", f"{start_sec:.2f}",
                "-i", str(dubbed_v2),
                "-t", f"{dur_sec:.2f}",
                "-ar", "32000", "-ac", "1",
                str(out_wav),
            ])
        elif fallback_wav.is_file():
            run_ffmpeg([
                "ffmpeg", "-y",
                "-i", str(fallback_wav),
                "-ar", "32000", "-ac", "1",
                str(out_wav),
            ])
        else:
            raise FileNotFoundError(f"找不到可用参考音频: {dubbed_v2} 或 {fallback_wav}")

    print("[完成] MiniMax H3 15 秒验证素材全部就绪！")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
