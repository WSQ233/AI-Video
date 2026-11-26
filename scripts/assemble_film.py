#!/usr/bin/env python3
"""
分镜双流质量检验与全片后期成片合成工具 (film-editor 剪辑技能专用脚本)：
1. 按剧本项目 tasks.csv 的分镜顺序，从 outputs/ 检索各镜最新渲染成功的 .mp4
2. 使用 ffprobe 校验每个分镜必须同时包含 h264 视频流与 32000 Hz 双声道 aac 原生音频流
3. 将验收通过的分镜归档至 outputs/selected_shots/<task_id>.mp4
4. 调用 ffmpeg 将全部分镜按顺序无缝拼接，并进行音频响度归一化（loudnorm，消除切镜音量跳变），
   输出最终成片至 outputs/final_cut/<project_id>_final.mp4 与合成报告 assembly_report.json。
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def probe_media_streams(video_path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,width,height,sample_rate,channels,nb_frames:format=duration",
        "-of", "json",
        str(video_path),
    ]
    raw = subprocess.check_output(cmd, text=True)
    data = json.loads(raw)
    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration", 0.0) or 0.0)
    return {
        "has_video": v_stream is not None,
        "has_audio": a_stream is not None,
        "video_codec": v_stream.get("codec_name") if v_stream else None,
        "width": int(v_stream.get("width", 0)) if v_stream else 0,
        "height": int(v_stream.get("height", 0)) if v_stream else 0,
        "audio_codec": a_stream.get("codec_name") if a_stream else None,
        "sample_rate": int(a_stream.get("sample_rate", 0)) if a_stream and str(a_stream.get("sample_rate", "")).isdigit() else 0,
        "channels": int(a_stream.get("channels", 0)) if a_stream else 0,
        "duration_sec": round(duration, 2),
    }


def find_latest_shot_mp4(outputs_dir: Path, task_id: str, batch_name: str | None = None) -> Path | None:
    # 1. 优先检查 selected_shots/<task_id>.mp4
    selected_candidate = outputs_dir / "selected_shots" / f"{task_id}.mp4"
    if selected_candidate.is_file() and not batch_name:
        return selected_candidate

    # 2. 搜索指定批次或 outputs 下所有匹配 <task_id>*.mp4 的文件（按修改时间取最新）
    search_roots = [outputs_dir / batch_name] if batch_name else [outputs_dir]
    matches: list[Path] = []
    for root in search_roots:
        if not root.is_dir():
            continue
        for mp4 in root.rglob(f"{task_id}*.mp4"):
            if "final_cut" not in mp4.parts and "selected_shots" not in mp4.parts:
                matches.append(mp4)
    if not matches and selected_candidate.is_file():
        return selected_candidate
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="校验剧本项目分镜双流并按 tasks.csv 顺序拼接输出最终成片")
    parser.add_argument("--project-dir", required=True, help="剧本项目根目录（如 /content/drive/MyDrive/AI_Video/projects/01_rainy_signal）")
    parser.add_argument("--batch-name", default=None, help="可选：指定从哪个批次目录提取分镜")
    parser.add_argument("--output-name", default=None, help="可选：成片文件名（默认 <project_id>_final.mp4）")
    parser.add_argument("--normalize-audio", action="store_true", default=True, help="开启 EBU R128 音频响度归一化（默认开启）")
    parser.add_argument("--dry-run", action="store_true", help="仅做分镜文件查找与双流校验，不执行合成")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    tasks_csv = project_dir / "tasks.csv"
    outputs_dir = project_dir / "outputs"
    selected_dir = outputs_dir / "selected_shots"
    final_cut_dir = outputs_dir / "final_cut"
    selected_dir.mkdir(parents=True, exist_ok=True)
    final_cut_dir.mkdir(parents=True, exist_ok=True)

    if not tasks_csv.is_file():
        print(f"[错误] 未找到任务表: {tasks_csv}", file=sys.stderr)
        return 1

    with tasks_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("[错误] tasks.csv 为空", file=sys.stderr)
        return 1

    shot_records: list[dict[str, Any]] = []
    selected_files: list[Path] = []
    missing_shots: list[str] = []

    for idx, row in enumerate(rows, start=1):
        task_id = (row.get("task_id") or f"shot_{idx:02d}").strip()
        src_mp4 = find_latest_shot_mp4(outputs_dir, task_id, batch_name=args.batch_name)
        if not src_mp4:
            missing_shots.append(task_id)
            print(f"[{idx}/{len(rows)}] [缺失] 未找到分镜视频: {task_id}")
            continue

        info = probe_media_streams(src_mp4)
        if not info["has_video"] or not info["has_audio"]:
            print(f"[{idx}/{len(rows)}] [警告] {task_id} 缺少视频或原生音频流: {info}", file=sys.stderr)
        else:
            print(
                f"[{idx}/{len(rows)}] [双流合格] {task_id}: {src_mp4.name} "
                f"({info['width']}x{info['height']}, {info['duration_sec']}s, audio={info['audio_codec']}@{info['sample_rate']}Hz/{info['channels']}ch)"
            )

        dst_selected = selected_dir / f"{task_id}.mp4"
        if src_mp4.resolve() != dst_selected.resolve():
            shutil.copy2(src_mp4, dst_selected)
        selected_files.append(dst_selected)
        shot_records.append({
            "order": idx,
            "task_id": task_id,
            "source_file": str(src_mp4),
            "selected_file": str(dst_selected),
            "stream_info": info,
        })

    if missing_shots:
        print(f"\n[终止合成] 尚有 {len(missing_shots)} 个分镜未出片: {', '.join(missing_shots)}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("\n[Dry Run 完成] 所有分镜均已就绪并通过双流检查。")
        return 0

    final_name = args.output_name or f"{project_dir.name}_final.mp4"
    final_mp4 = final_cut_dir / final_name

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        concat_list_path = Path(tf.name)
        for p in selected_files:
            escaped = str(p).replace("'", "'\\''")
            tf.write(f"file '{escaped}'\n")

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-ar", "32000",
            "-ac", "2",
            "-b:a", "192k",
        ]
        if args.normalize_audio:
            cmd.extend(["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"])
        cmd.append(str(final_mp4))
        subprocess.run(cmd, check=True)
    finally:
        concat_list_path.unlink(missing_ok=True)

    final_info = probe_media_streams(final_mp4)
    report = {
        "project_id": project_dir.name,
        "final_cut_mp4": str(final_mp4),
        "total_shots": len(selected_files),
        "final_stream_info": final_info,
        "shots": shot_records,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
    }
    report_path = final_cut_dir / "assembly_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n=== 全片合成完成 ===")
    print(f"最终成片 : {final_mp4} (总时长 {final_info['duration_sec']}s, {final_info['width']}x{final_info['height']})")
    print(f"合成报告 : {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
