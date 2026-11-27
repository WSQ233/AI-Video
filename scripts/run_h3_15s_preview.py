#!/usr/bin/env python3
"""
MiniMax H3 Ref2VA 15 秒原片编辑验证一键流水线（专为 Colab A100 打造）：
1. 自动探测 GPU 显存：>=75GB (A100-80GB/H100) 使用 33.1B 未剪枝 BF16，否则使用 33.1B 未剪枝 INT8-ConvRot
2. 仅预热当前必需的 1 套 Ref2VA 主权重 + Turbo LoRA（通过 setup_env.py Drive API Turbo 极速直下）
3. 裁切 02_yongzheng_ep12_huang 原片前 15 秒的 3 个单镜参考片段（去字幕带 + 24fps 1280x704）与角色参考音轨
4. 以 --bf16-vae --cache-none 启动无头 ComfyUI，执行 batch_runner.py 渲染 tasks_h3_15s_test.csv
5. 完成后关闭 ComfyUI，将 3 镜 H3 原生音画成片无缝拼接并做 EBU R128 响度归一化，落盘至项目 outputs/final_cut/
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path


def detect_vram_gb() -> float:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            text=True,
        ).strip()
        first = out.splitlines()[0].strip()
        return float(first) / 1024.0
    except Exception as exc:
        print(f"[警告] 无法通过 nvidia-smi 检测显存 ({exc})，默认按 40GB 保守处理")
        return 40.0


def find_shot_output(batch_dir: Path, task_id: str) -> Path:
    candidates = sorted(batch_dir.glob(f"{task_id}*.mp4"))
    if not candidates:
        raise FileNotFoundError(f"找不到任务 {task_id} 的输出 MP4: {batch_dir}")
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 MiniMax H3 15 秒原片角色/台词替换验证流水线")
    parser.add_argument("--repo-root", default="/content/AI-Video")
    parser.add_argument("--project", default="02_yongzheng_ep12_huang")
    parser.add_argument("--batch-name", default="h3_15s_test_v1")
    parser.add_argument("--drive-root", default="/content/drive/MyDrive/AI_Video")
    parser.add_argument("--stage-backend", default="auto")
    parser.add_argument("--range-workers", type=int, default=16)
    parser.add_argument("--force-unet", default="", help="可选：手动指定 33.1B 未剪枝模型文件名")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    project_dir = Path(args.drive_root) / "projects" / args.project
    vram_gb = detect_vram_gb()
    print(f"[硬件探测] 当前 GPU 显存: {vram_gb:.1f} GB")

    if args.force_unet.strip():
        override_unet = args.force_unet.strip()
        pack_name = "minimax_h3_ref2va_int8_full" if "int8" in override_unet.lower() else "minimax_h3_ref2va_bf16"
    elif vram_gb >= 75.0:
        override_unet = "minimax_h3_ref2va_bf16.safetensors"
        pack_name = "minimax_h3_ref2va_bf16"
    else:
        override_unet = "minimax_h3_ref2va_int8_convrot.safetensors"
        pack_name = "minimax_h3_ref2va_int8_full"

    print(f"[模型选择] 强制使用默认引擎 MiniMax H3 33.1B 未剪枝版: pack={pack_name} | unet={override_unet}")

    # 1. 部署 ComfyUI 并仅预热必需的 1 套 Ref2VA 模型包 + Turbo LoRA
    setup_cmd = [
        sys.executable, "-u", str(repo_root / "scripts" / "setup_env.py"),
        "--repo-root", str(repo_root),
        "--project", args.project,
        "--mode", "copy_to_local",
        "--stage-backend", args.stage_backend,
        "--range-workers", str(args.range_workers),
        "--packs", pack_name, "minimax_h3_turbo_lora",
    ]
    print("[阶段 1/4] 执行环境初始化与模型极速预热...")
    subprocess.run(setup_cmd, check=True)

    # 2. 裁切 15 秒三镜干净参考视频与纯净中文参考音轨
    print("[阶段 2/4] 裁切 15 秒原片三镜参考片段（无字幕）与声纹参考音轨...")
    subprocess.run(
        [
            sys.executable, "-u", str(repo_root / "scripts" / "prep_h3_15s_clips.py"),
            "--project-dir", str(project_dir),
            "--repo-root", str(repo_root),
        ],
        check=True,
    )

    # 3. 启动无头 ComfyUI（强制 --bf16-vae --cache-none）并运行 MiniMax H3 Ref2VA 批处理
    launch_info = json.loads(Path("/content/ComfyUI/launch_info.json").read_text(encoding="utf-8"))
    comfy_dir = launch_info["comfyui_dir"]
    comfy_args = [a for a in shlex.split(launch_info["comfyui_args"]) if a != "--normalvram"]
    for flag in ("--bf16-vae", "--cache-none"):
        if flag not in comfy_args:
            comfy_args.append(flag)
    if vram_gb < 35.0:
        for flag in ("--lowvram", "--disable-pinned-memory"):
            if flag not in comfy_args:
                comfy_args.append(flag)

    log_file = project_dir / "logs" / f"comfyui_{args.batch_name}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"[阶段 3/4] 启动无头 ComfyUI ({' '.join(comfy_args)}) 并运行 MiniMax H3 Ref2VA 3 镜批处理...")

    log_fp = log_file.open("a", encoding="utf-8")
    server_proc = subprocess.Popen(
        [sys.executable, "main.py", *comfy_args],
        cwd=comfy_dir,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
    )
    runner_rc = 1
    try:
        runner_cmd = [
            sys.executable, "-u", str(repo_root / "scripts" / "batch_runner.py"),
            "--tasks-csv", str(project_dir / "tasks_h3_15s_test.csv"),
            "--workflows-dir", str(project_dir / "workflows"),
            "--shared-workflows-dir", str(Path(args.drive_root) / "shared" / "workflows"),
            "--output-dir", str(project_dir / "outputs"),
            "--project-dir", str(project_dir),
            "--batch-name", args.batch_name,
            "--override-unet", override_unet,
        ]
        if vram_gb < 35.0:
            print(f"[显存保护] 检测到 {vram_gb:.1f}GB 显存 (<35GB)，自动启用 --tiled-vae 防长镜头解码 OOM")
            runner_cmd.append("--tiled-vae")
        res = subprocess.run(runner_cmd, check=False)
        runner_rc = res.returncode
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        log_fp.close()

    if runner_rc != 0:
        raise RuntimeError(f"MiniMax H3 批处理未完全成功 (exit={runner_rc})，请查看日志: {log_file}")

    # 4. 拼接 4 镜 H3 原生音视频输出并做 EBU R128 响度归一化（严禁添加任何字幕）
    print("[阶段 4/4] 拼接 4 镜 H3 原生音视频成片（无字幕）并执行 ffprobe 质检...")
    batch_dir = project_dir / "outputs" / args.batch_name
    shot_specs = [
        ("h3_15s_s01_trump", 0.0),
        ("h3_15s_s02_vance", 0.40),  # 裁掉原片 3.85s 切点前 0.4s 横移边缘，保证纯万斯画面
        ("h3_15s_s03a_rubio", 0.0),
        ("h3_15s_s03b_rubio", 0.0),
    ]
    shot_items = [(find_shot_output(batch_dir, tid), trim_start) for tid, trim_start in shot_specs]
    print("[已定位成片]", [(str(p), ts) for p, ts in shot_items])

    final_dir = project_dir / "outputs" / "final_cut"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_out = final_dir / f"{args.project}_h3_15s_preview.mp4"

    # 使用 filter_complex 统一帧率/采样率拼接 + EBU R128 loudnorm，确保无缝音画同步
    filter_parts = []
    concat_inputs = []
    for i, (_p, trim_start) in enumerate(shot_items):
        v_trim = f"trim=start={trim_start:.2f},setpts=PTS-STARTPTS," if trim_start > 0 else ""
        a_trim = f"atrim=start={trim_start:.2f},asetpts=PTS-STARTPTS," if trim_start > 0 else ""
        filter_parts.append(
            f"[{i}:v]{v_trim}fps=24,scale=960:544:flags=lanczos,setsar=1,format=yuv420p[v{i}]"
        )
        filter_parts.append(
            f"[{i}:a]{a_trim}aresample=32000:async=1,aformat=channel_layouts=stereo[a{i}]"
        )
        concat_inputs.append(f"[v{i}][a{i}]")
    filter_parts.append(
        f"{''.join(concat_inputs)}concat=n={len(shot_items)}:v=1:a=1[vcat][acat]"
    )
    filter_parts.append("[acat]loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    filter_complex = ";".join(filter_parts)

    ffmpeg_cmd = ["ffmpeg", "-y"]
    for p, _ts in shot_items:
        ffmpeg_cmd.extend(["-i", str(p)])
    ffmpeg_cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vcat]",
        "-map", "[aout]",
        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "32000", "-ac", "2",
        "-movflags", "+faststart",
        str(final_out),
    ])
    subprocess.run(ffmpeg_cmd, check=True)

    probe_out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,sample_rate,channels",
            "-of", "json", str(final_out),
        ],
        text=True,
    )
    print(f"[验收完成] MiniMax H3 15 秒预览成片已落盘: {final_out}")
    print(probe_out)
    os.sync()
    time.sleep(5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
