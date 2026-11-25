#!/usr/bin/env python3
"""
Colab H100 无头批处理调度器：
- 读取 Google Drive 上的任务表 (tasks.csv)
- 逐条替换 ComfyUI API Workflow 模板占位符并提交到本地 ComfyUI (127.0.0.1:8188)
- 支持 task_id 幂等去重与断点续传，每完成一条立即写入 manifest.jsonl 到 Google Drive
- 单条失败自动隔离记录，绝不拖死整批任务
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


def http_json(url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
    parser = argparse.ArgumentParser(description="ComfyUI Headless 批处理执行器（按项目目录隔离，支持断点续传）")
    parser.add_argument("--tasks-csv", required=True, help="项目任务表 tasks.csv 路径")
    parser.add_argument("--workflows-dir", required=True, help="项目专属工作流目录")
    parser.add_argument("--shared-workflows-dir", default=None, help="全局共享工作流目录（项目目录未找到时自动兜底）")
    parser.add_argument("--output-dir", required=True, help="项目输出目录")
    parser.add_argument("--batch-name", default=None, help="批次目录名（默认按日期生成）")
    parser.add_argument("--server", default="http://127.0.0.1:8188", help="ComfyUI API 地址")
    parser.add_argument("--timeout", type=int, default=1800, help="单条任务超时时间（秒）")
    args = parser.parse_args()

    batch_name = args.batch_name or datetime.now().strftime("batch_%Y%m%d")
    out_dir = Path(args.output_dir)
    manifest_path = out_dir / batch_name / "manifest.jsonl"
    workflows_dir = Path(args.workflows_dir)
    shared_workflows_dir = Path(args.shared_workflows_dir) if args.shared_workflows_dir else None

    wait_server_ready(args.server)
    completed = load_completed_ids(manifest_path)
    print(f"[断点续传] 当前批次 {batch_name} 已完成 {len(completed)} 条任务")

    with Path(args.tasks_csv).open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ok_count = 0
    fail_count = 0
    skip_count = 0

    for idx, row in enumerate(rows, start=1):
        task_id = (row.get("task_id") or f"task_{idx:03d}").strip()
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
        replacements: dict[str, Any] = {
            "__TASK_ID__": task_id,
            "__PROMPT__": row.get("prompt", ""),
            "__NEGATIVE_PROMPT__": row.get("negative_prompt", ""),
            "__IMAGE__": row.get("image", ""),
            "__SEED__": seed,
            "__WIDTH__": int(row["width"]) if (row.get("width") or "").strip().isdigit() else 1344,
            "__HEIGHT__": int(row["height"]) if (row.get("height") or "").strip().isdigit() else 768,
            "__FRAMES__": int(row["frames"]) if (row.get("frames") or "").strip().isdigit() else 124,
            "__FPS__": int(row["fps"]) if (row.get("fps") or "").strip().isdigit() else 24,
            "__OUTPUT_PREFIX__": f"{batch_name}/{task_id}",
        }

        template_obj = json.loads(wf_path.read_text(encoding="utf-8"))
        prompt_graph = render_workflow(template_obj, replacements)

        print(f"[{idx}/{total}] 开始执行 {task_id} (workflow={wf_name}, seed={seed})...")
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
                "prompt": row.get("prompt", ""),
                "image": row.get("image", ""),
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
