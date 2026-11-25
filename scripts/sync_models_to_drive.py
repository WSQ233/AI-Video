#!/usr/bin/env python3
"""
将 Hugging Face 开源模型按 pack 高速同步到 5TB Google Drive。
推荐在 Colab 免费 CPU 运行时执行，消耗 0 H100 算力单元 (CU)。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


DRIVE_SHARED_SUBDIRS = [
    "shared/models/diffusion_models",
    "shared/models/text_encoders",
    "shared/models/vae",
    "shared/models/loras",
    "shared/models/upscale_models",
    "shared/models/latent_upscale_models",
    "shared/models/clip_vision",
    "shared/workflows",
    "shared/logs",
    "projects",
]

PROJECT_SUBDIRS = [
    "inputs",
    "workflows",
    "outputs",
    "logs",
]


def ensure_drive_layout(drive_root: Path, repo_root: Path | None = None, project_id: str | None = None) -> None:
    """初始化 5TB Google Drive 全局共享层与独立项目文件夹，并将仓库中的共享工作流与剧本/任务表同步上云。"""
    for rel in DRIVE_SHARED_SUBDIRS:
        (drive_root / rel).mkdir(parents=True, exist_ok=True)
    if repo_root and (repo_root / "workflows" / "shared").exists():
        for wf in (repo_root / "workflows" / "shared").glob("*.json"):
            dst = drive_root / "shared" / "workflows" / wf.name
            if not dst.exists():
                shutil.copy2(wf, dst)
    print(f"[云端共享层就绪] {drive_root / 'shared'}")

    # 将仓库中所有 projects/* 同步初始化到 5TB 云盘对应项目目录（不覆盖用户在云盘修改过的同名文件）
    projects_to_init: list[str] = []
    if repo_root and (repo_root / "projects").exists():
        for p in sorted((repo_root / "projects").iterdir()):
            if p.is_dir():
                projects_to_init.append(p.name)
    if project_id and project_id not in projects_to_init:
        projects_to_init.append(project_id)

    for pid in projects_to_init:
        cloud_pdir = drive_root / "projects" / pid
        for sub in PROJECT_SUBDIRS:
            (cloud_pdir / sub).mkdir(parents=True, exist_ok=True)
        if repo_root:
            src_pdir = repo_root / "projects" / pid
            if src_pdir.exists():
                for fname in ("project.json", "script.md", "tasks.csv"):
                    src_file = src_pdir / fname
                    dst_file = cloud_pdir / fname
                    if src_file.exists() and not dst_file.exists():
                        shutil.copy2(src_file, dst_file)
                src_wf = src_pdir / "workflows"
                if src_wf.exists():
                    for wf in src_wf.glob("*.json"):
                        dst_wf = cloud_pdir / "workflows" / wf.name
                        if not dst_wf.exists():
                            shutil.copy2(wf, dst_wf)
        print(f"[云端项目就绪] {cloud_pdir}")


def resolve_repo_path(
    api: Any,
    repo_id: str,
    preferred_path: str,
    fallback_keywords: list[str],
    exclude_keywords: list[str],
    token: str | None,
) -> str:
    """优先使用配置中的精确路径；若上游目录微调，则按关键词自动匹配并排除指定词（如 pruned）。"""
    try:
        files = api.list_repo_files(repo_id=repo_id, token=token)
    except Exception as exc:
        print(f"  [警告] 无法列出仓库 {repo_id} 文件列表 ({exc})，将直接尝试精确路径。")
        return preferred_path

    if preferred_path in files:
        return preferred_path

    if fallback_keywords:
        lowered = [kw.lower() for kw in fallback_keywords]
        excluded = [kw.lower() for kw in exclude_keywords]
        candidates = [
            f for f in files
            if all(kw in f.lower() for kw in lowered)
            and not any(ex in f.lower() for ex in excluded)
        ]
        if len(candidates) == 1:
            print(f"  [自动修正路径] {preferred_path} -> {candidates[0]}")
            return candidates[0]
        if len(candidates) > 1:
            candidates.sort(key=len)
            print(f"  [自动修正路径] 匹配到多个候选，选用最短路径: {candidates[0]}")
            return candidates[0]

    raise FileNotFoundError(
        f"仓库 {repo_id} 中未找到 {preferred_path}（关键词 {fallback_keywords} 也无匹配）。"
        f"请检查模型仓库或更新 configs/models_manifest.json。"
    )


def download_file_to_drive(
    entry: dict[str, Any],
    drive_models_root: Path,
    token: str | None,
    force: bool = False,
) -> None:
    from huggingface_hub import HfApi, hf_hub_download

    target_dir = drive_models_root / entry["target_subdir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / entry["filename"]

    if final_path.exists() and final_path.stat().st_size > 1024 * 1024 and not force:
        size_gb = final_path.stat().st_size / (1024 ** 3)
        print(f"  [已存在跳过] {entry['target_subdir']}/{entry['filename']} ({size_gb:.2f} GB)")
        return

    api = HfApi()
    repo_id = entry["repo_id"]
    repo_path = resolve_repo_path(
        api=api,
        repo_id=repo_id,
        preferred_path=entry["repo_path"],
        fallback_keywords=entry.get("fallback_keywords", []),
        exclude_keywords=entry.get("exclude_keywords", []),
        token=token,
    )

    print(f"  [开始下载] {repo_id} :: {repo_path}")
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="hf_dl_") as tmp_dir:
        local_cached = hf_hub_download(
            repo_id=repo_id,
            filename=repo_path,
            local_dir=tmp_dir,
            token=token,
        )
        # 先落临时文件再原子替换，避免中断在网盘留下损坏文件
        tmp_drive_path = final_path.with_suffix(final_path.suffix + ".part")
        if tmp_drive_path.exists():
            tmp_drive_path.unlink()
        shutil.copy2(local_cached, tmp_drive_path)
        os.replace(tmp_drive_path, final_path)

    elapsed = time.time() - t0
    size_gb = final_path.stat().st_size / (1024 ** 3)
    speed_mb = (final_path.stat().st_size / (1024 ** 2)) / max(elapsed, 0.1)
    print(f"  [同步完成] {final_path} ({size_gb:.2f} GB, 耗时 {elapsed:.1f}s, ~{speed_mb:.1f} MB/s)")


def main() -> int:
    parser = argparse.ArgumentParser(description="将开源视频模型包同步到 Google Drive 5TB")
    parser.add_argument("--manifest", default="configs/models_manifest.json", help="模型清单路径")
    parser.add_argument("--repo-root", default=".", help="AI-Video 仓库根目录（用于同步 projects/ 剧本上云）")
    parser.add_argument("--project", default="01_rainy_signal", help="同步初始化的项目 ID")
    parser.add_argument("--drive-root", default=None, help="Google Drive 项目根目录")
    parser.add_argument("--packs", nargs="+", required=True, help="要同步的模型包 ID 列表，或传 all")
    parser.add_argument("--hf-token", default=os.environ.get("HF_TOKEN"), help="Hugging Face Token（下载受限模型时需要）")
    parser.add_argument("--force", action="store_true", help="强制重新下载覆盖已有文件")
    parser.add_argument("--list", action="store_true", help="仅列出所有可用模型包")
    args = parser.parse_args()

    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    packs_cfg: dict[str, Any] = manifest["packs"]

    if args.list:
        for pid, info in packs_cfg.items():
            token_tag = "需HF_TOKEN" if info.get("requires_hf_token") else "免Token"
            print(f"- {pid:22s} | ~{info['estimated_gb']:3}GB | {token_tag} | {info['label']}")
        return 0

    drive_root = Path(args.drive_root or manifest["drive_root_default"])
    ensure_drive_layout(drive_root, repo_root=Path(args.repo_root).resolve(), project_id=args.project)
    drive_models_root = drive_root / "shared" / "models"

    selected = list(packs_cfg.keys()) if "all" in args.packs else args.packs
    for pid in selected:
        if pid not in packs_cfg:
            print(f"[错误] 未知模型包: {pid}。可选: {', '.join(packs_cfg.keys())}", file=sys.stderr)
            return 1

    for pid in selected:
        pack = packs_cfg[pid]
        print(f"\n=== 同步模型包: {pid} ({pack['label']}, 约 {pack['estimated_gb']} GB) ===")
        if pack.get("requires_hf_token") and not args.hf_token:
            print(
                f"  [跳过] {pid} 需要 HF_TOKEN，请先在 Hugging Face 同意协议并通过 --hf-token 或环境变量 HF_TOKEN 传入。",
                file=sys.stderr,
            )
            continue
        for entry in pack["files"]:
            download_file_to_drive(
                entry=entry,
                drive_models_root=drive_models_root,
                token=args.hf_token,
                force=args.force,
            )

    print("\n[全部完成] 模型资源已存入 Google Drive，可切换至 H100 运行时直接生成！")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
