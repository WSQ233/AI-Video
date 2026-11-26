#!/usr/bin/env python3
"""
Colab A100 / H100 无头批处理调度器（按剧本项目目录隔离）：
- 读取剧本项目下的任务表 (tasks.csv)
- 优先加载该剧本项目 workflows/ 下的专属 ComfyUI API Workflow 模板
- 自动解析项目下 characters/<character_id>/（含 outfits/）、images/（含 scenes/、props/、keyframes/）中的参考图
- 支持单图 (__IMAGE__) 与双参考图/首尾帧 (__IMAGE_2__，对应 tasks.csv 可选列 image_2)
- 支持 --only-tasks 过滤（支持「阶段 A：仅跑定妆立锚镜」与「阶段 B：跑全片 Ref2VA 分镜」分阶段渲染）
- 强制校验 MiniMax H3 15 秒时长上限（frames / fps <= 15.0，且满足 17k+5 帧数时间网格）
- 支持 task_id 幂等去重与断点续传，每完成一条立即写入 manifest.jsonl 到项目 outputs/
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_H3_DURATION_SEC = 15.0


def snap_to_h3_frame_grid(frames: int, fps: int = 24) -> int:
    """将帧数对齐到 MiniMax H3 的 17k + 5 时间网格，并严格限制在 15 秒上限以内（24fps 下最大 345 帧 = 14.38s）。"""
    max_valid_frames = 345 if fps == 24 else int(MAX_H3_DURATION_SEC * fps)
    clamped = max(5, min(frames, max_valid_frames))
    snapped = clamped + (5 - (clamped % 17)) % 17
    if snapped > max_valid_frames:
        snapped -= 17
    return max(5, snapped)


def resolve_project_image(image_ref: str, project_dir: Path, comfy_input_dir: Path | None = None) -> str:
    """
    解析 tasks.csv 中的 image / image_2 / video 字段（支持 characters/<id>/...、images/scenes/<sid>/...、
    images/keyframes/...、images/props/...、videos/source_clips/... 或简写文件名），
    确保其在 ComfyUI/input 中可被 LoadImage / VHS_LoadVideo 定位。
    """
    clean = (image_ref or "").strip().replace("\\", "/")
    if not clean:
        return ""

    candidates: list[tuple[str, Path]] = [
        (clean, project_dir / clean),
    ]
    fname = Path(clean).name
    if (project_dir / "characters").exists():
        for char_dir in sorted((project_dir / "characters").iterdir()):
            if char_dir.is_dir():
                candidates.append((f"characters/{char_dir.name}/{fname}", char_dir / fname))
                candidates.append((f"characters/{char_dir.name}/outfits/{fname}", char_dir / "outfits" / fname))
    if (project_dir / "images").exists():
        candidates.append((f"images/{fname}", project_dir / "images" / fname))
        candidates.append((f"images/keyframes/{fname}", project_dir / "images" / "keyframes" / fname))
        candidates.append((f"images/props/{fname}", project_dir / "images" / "props" / fname))
        if (project_dir / "images" / "scenes").exists():
            for sdir in sorted((project_dir / "images" / "scenes").iterdir()):
                if sdir.is_dir():
                    candidates.append((f"images/scenes/{sdir.name}/{fname}", sdir / fname))
    if (project_dir / "videos").exists():
        candidates.append((f"videos/{fname}", project_dir / "videos" / fname))
        candidates.append((f"videos/source_clips/{fname}", project_dir / "videos" / "source_clips" / fname))
    candidates.append((f"inputs/{fname}", project_dir / "inputs" / fname))

    for rel_path, full_path in candidates:
        if full_path.is_file():
            if comfy_input_dir and comfy_input_dir.is_dir():
                # ComfyUI 原生 LoadImage 校验仅枚举 input/ 顶层文件，优先返回指向同一文件的平铺文件名
                flat_link = comfy_input_dir / fname
                if flat_link.exists() or flat_link.is_symlink():
                    try:
                        if flat_link.resolve() == full_path.resolve():
                            return fname
                    except Exception:
                        pass
                else:
                    try:
                        flat_link.symlink_to(full_path)
                        return fname
                    except Exception:
                        pass
                # 若根目录已有同名不同文件，则创建唯一扁平化软链接避免 LoadImage 路径校验报错
                unique_flat = rel_path.replace("/", "__")
                unique_link = comfy_input_dir / unique_flat
                if not unique_link.exists() and not unique_link.is_symlink():
                    try:
                        unique_link.symlink_to(full_path)
                    except Exception:
                        pass
                if unique_link.exists():
                    return unique_flat
                target_in_comfy = comfy_input_dir / rel_path
                if target_in_comfy.is_file():
                    return rel_path
            return rel_path
    return clean


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body}") from exc


def wait_server_ready(base_url: str, timeout_sec: int = 180) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            http_json(f"{base_url}/system_stats", timeout=5)
            print(f"[就绪] ComfyUI 服务已启动: {base_url}")
            return
        except Exception:
            time.sleep(2)
    raise TimeoutError(f"等待 ComfyUI 启动超时 ({timeout_sec}s): {base_url}")


def load_completed_ids(manifest_path: Path) -> set[str]:
    done: set[str] = set()
    if not manifest_path.exists():
        return done
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
            if rec.get("status") == "ok" and rec.get("task_id"):
                done.add(str(rec["task_id"]))
        except json.JSONDecodeError:
            continue
    return done


def render_workflow(template_obj: Any, replacements: dict[str, Any]) -> Any:
    """递归替换工作流 JSON 中的占位符（支持纯字符串替换和数值类型保留）。"""
    if isinstance(template_obj, dict):
        return {k: render_workflow(v, replacements) for k, v in template_obj.items()}
    if isinstance(template_obj, list):
        return [render_workflow(v, replacements) for v in template_obj]
    if isinstance(template_obj, str):
        if template_obj in replacements:
            return replacements[template_obj]
        result = template_obj
        for k, v in replacements.items():
            if k in result:
                result = result.replace(k, str(v))
        return result
    return template_obj


def poll_prompt(base_url: str, prompt_id: str, poll_interval: float = 3.0, timeout_sec: int = 1800) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        hist = http_json(f"{base_url}/history/{prompt_id}", timeout=15)
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(poll_interval)
    raise TimeoutError(f"任务 {prompt_id} 执行超时 ({timeout_sec}s)")


def extract_output_files(history_entry: dict[str, Any]) -> list[str]:
    files: list[str] = []
    outputs = history_entry.get("outputs", {})
    for node_out in outputs.values():
        for key in ("gifs", "videos", "images"):
            for item in node_out.get(key, []):
                sub = item.get("subfolder", "")
                name = item.get("filename", "")
                if name:
                    files.append(f"{sub}/{name}" if sub else name)
    return files


def append_manifest(manifest_path: Path, record: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="ComfyUI Headless 批处理执行器（按剧本项目目录隔离，支持分阶段与断点续传）")
    parser.add_argument("--tasks-csv", required=True, help="剧本项目任务表 tasks.csv 路径")
    parser.add_argument("--workflows-dir", required=True, help="剧本项目专属工作流目录")
    parser.add_argument("--shared-workflows-dir", default=None, help="全局共享工作流目录（项目目录未找到时自动兜底）")
    parser.add_argument("--output-dir", required=True, help="剧本项目输出目录")
    parser.add_argument("--project-dir", default=None, help="剧本项目根目录（默认取 tasks.csv 所在目录）")
    parser.add_argument("--comfy-input-dir", default="/content/ComfyUI/input", help="ComfyUI input 挂载目录")
    parser.add_argument("--batch-name", default=None, help="批次目录名（默认按日期生成）")
    parser.add_argument("--only-tasks", nargs="*", default=None, help="可选：仅执行指定的 task_id 列表（如阶段 A 定妆立锚镜）")
    parser.add_argument("--server", default="http://127.0.0.1:8188", help="ComfyUI API 地址")
    parser.add_argument("--timeout", type=int, default=1800, help="单条任务超时时间（秒）")
    args = parser.parse_args()

    tasks_csv_path = Path(args.tasks_csv).resolve()
    project_dir = Path(args.project_dir).resolve() if args.project_dir else tasks_csv_path.parent
    comfy_input_dir = Path(args.comfy_input_dir) if args.comfy_input_dir else None
    batch_name = args.batch_name or datetime.now().strftime("batch_%Y%m%d")
    out_dir = Path(args.output_dir)
    manifest_path = out_dir / batch_name / "manifest.jsonl"
    workflows_dir = Path(args.workflows_dir)
    shared_workflows_dir = Path(args.shared_workflows_dir) if args.shared_workflows_dir else None
    only_filter = set(args.only_tasks) if args.only_tasks else None

    wait_server_ready(args.server)
    completed = load_completed_ids(manifest_path)
    print(f"[断点续传] 当前批次 {batch_name} 已完成 {len(completed)} 条任务")

    with tasks_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ok_count = 0
    fail_count = 0
    skip_count = 0

    for idx, row in enumerate(rows, start=1):
        task_id = (row.get("task_id") or f"task_{idx:03d}").strip()
        if only_filter is not None and task_id not in only_filter:
            continue
        if task_id in completed:
            print(f"[{idx}/{total}] 跳过已完成: {task_id}")
            skip_count += 1
            continue

        wf_name = (row.get("workflow") or "").strip()
        wf_path = workflows_dir / wf_name
        if not wf_path.exists() and shared_workflows_dir:
            shared_candidate = shared_workflows_dir / wf_name
            if shared_candidate.exists():
                wf_path = shared_candidate
        if not wf_path.exists():
            print(f"[{idx}/{total}] [失败] 找不到工作流模板: {wf_path}")
            append_manifest(manifest_path, {
                "task_id": task_id,
                "status": "error",
                "error": f"workflow not found: {wf_path}",
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            fail_count += 1
            continue

        seed_raw = (row.get("seed") or "").strip()
        seed = int(seed_raw) if seed_raw.isdigit() else random.randint(1, 2**31 - 1)
        fps = int(row["fps"]) if (row.get("fps") or "").strip().isdigit() else 24
        raw_frames = int(row["frames"]) if (row.get("frames") or "").strip().isdigit() else 124
        frames = snap_to_h3_frame_grid(raw_frames, fps=fps)
        if frames != raw_frames:
            print(
                f"  [H3 15s/17k+5 网格修正] {task_id}: 原帧数 {raw_frames} ({raw_frames / fps:.2f}s) "
                f"-> 已对齐至合法网格 {frames} 帧 ({frames / fps:.2f}s <= 15s)"
            )

        resolved_image = resolve_project_image(row.get("image", ""), project_dir, comfy_input_dir)
        resolved_image_2 = resolve_project_image(row.get("image_2", ""), project_dir, comfy_input_dir)
        resolved_image_3 = resolve_project_image(row.get("image_3", ""), project_dir, comfy_input_dir)
        resolved_video = resolve_project_image(row.get("video", ""), project_dir, comfy_input_dir)
        replacements: dict[str, Any] = {
            "__TASK_ID__": task_id,
            "__PROMPT__": row.get("prompt", ""),
            "__NEGATIVE_PROMPT__": row.get("negative_prompt", ""),
            "__IMAGE__": resolved_image,
            "__IMAGE_2__": resolved_image_2,
            "__IMAGE_3__": resolved_image_3,
            "__VIDEO__": resolved_video,
            "__SEED__": seed,
            "__WIDTH__": int(row["width"]) if (row.get("width") or "").strip().isdigit() else 1344,
            "__HEIGHT__": int(row["height"]) if (row.get("height") or "").strip().isdigit() else 768,
            "__FRAMES__": frames,
            "__FPS__": fps,
            "__OUTPUT_PREFIX__": f"{batch_name}/{task_id}",
        }

        template_obj = json.loads(wf_path.read_text(encoding="utf-8"))
        prompt_graph = render_workflow(template_obj, replacements)

        print(
            f"[{idx}/{total}] 开始执行 {task_id} "
            f"(workflow={wf_name}, frames={frames}/{fps}fps={frames/fps:.2f}s, "
            f"image={resolved_image or 'None'}, image_2={resolved_image_2 or 'None'}, image_3={resolved_image_3 or 'None'}, video={resolved_video or 'None'}, seed={seed})..."
        )
        t0 = time.time()
        try:
            res = http_json(f"{args.server}/prompt", payload={"prompt": prompt_graph})
            prompt_id = res["prompt_id"]
            hist_entry = poll_prompt(args.server, prompt_id, timeout_sec=args.timeout)
            files = extract_output_files(hist_entry)
            elapsed = round(time.time() - t0, 2)
            append_manifest(manifest_path, {
                "task_id": task_id,
                "status": "ok",
                "workflow": wf_name,
                "seed": seed,
                "frames": frames,
                "duration_sec": round(frames / fps, 2),
                "prompt": row.get("prompt", ""),
                "image": resolved_image,
                "image_2": resolved_image_2,
                "image_3": resolved_image_3,
                "video": resolved_video,
                "outputs": files,
                "elapsed_sec": elapsed,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            print(f"  [成功] {task_id} 用时 {elapsed}s -> {files}")
            ok_count += 1
        except Exception as exc:
            elapsed = round(time.time() - t0, 2)
            print(f"  [失败] {task_id} 用时 {elapsed}s: {exc}")
            append_manifest(manifest_path, {
                "task_id": task_id,
                "status": "error",
                "workflow": wf_name,
                "seed": seed,
                "error": str(exc),
                "elapsed_sec": elapsed,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            fail_count += 1

    print(f"\n=== 批处理结束: 成功 {ok_count} | 跳过 {skip_count} | 失败 {fail_count} ===")
    print(f"记录文件: {manifest_path}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
