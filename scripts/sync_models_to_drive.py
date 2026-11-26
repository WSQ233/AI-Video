#!/usr/bin/env python3
"""
将 Hugging Face 开源模型按 pack 高速同步到 5TB Google Drive，
并按剧本项目维度同步初始化所有 projects/<project_id>/ 的完整目录结构与专属 ComfyUI 流程。

高性能双引擎架构（推荐在 Colab 免费 CPU 0 CU 运行）：
1. 首选引擎 (drive_api)：绕过 DriveFS FUSE，使用多线程 HTTP Range 滑动窗口预取 +
   Google Drive v3 Resumable Upload 64MiB 内存流水线直传（本地磁盘占用 0 GB，多文件并行，
   自带精确字节数与 LFS SHA256 校验、断点续传与原子覆盖）。
2. 自动回退 (drivefs)：未授权 Drive API 时自动回退至顺序写调优的 aria2c / hf_hub_download，
   同样具备精确字节数校验与原子替换，确保零失败兼容。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# 允许脚本以 `python scripts/sync_models_to_drive.py` 直接执行并导入同目录模块
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from drive_fast_io import (  # noqa: E402
    DEFAULT_FETCH_WORKERS,
    DEFAULT_UPLOAD_CHUNK_MB,
    GoogleDriveClient,
    copy_file_fast,
    drive_path_to_rel_parts,
    try_create_drive_client,
)


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
    "images/scenes",
    "images/props",
    "images/keyframes",
    "videos/source_clips",
    "characters",
    "audio",
    "workflows",
    "outputs/raw_batches",
    "outputs/selected_shots",
    "outputs/extracted_frames",
    "outputs/final_cut",
    "logs",
]


def ensure_drive_layout(drive_root: Path, repo_root: Path | None = None, project_id: str | None = None) -> None:
    """初始化 5TB Google Drive 全局共享层与独立剧本项目文件夹，并将仓库中的项目剧本/分镜/人物设定/专属工作流同步上云。"""
    for rel in DRIVE_SHARED_SUBDIRS:
        (drive_root / rel).mkdir(parents=True, exist_ok=True)
    if repo_root and (repo_root / "workflows" / "shared").exists():
        for wf in (repo_root / "workflows" / "shared").glob("*.json"):
            dst = drive_root / "shared" / "workflows" / wf.name
            if not dst.exists():
                shutil.copy2(wf, dst)
    print(f"[云端共享层就绪] {drive_root / 'shared'}", flush=True)

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
                for fname in ("project.json", "source_script.md", "storyboard.md", "tasks.csv", "script.md"):
                    src_file = src_pdir / fname
                    dst_file = cloud_pdir / fname
                    if src_file.exists() and not dst_file.exists():
                        shutil.copy2(src_file, dst_file)

                for tree_sub in ("characters", "images", "videos", "audio"):
                    src_tree = src_pdir / tree_sub
                    if src_tree.exists():
                        for item in src_tree.rglob("*"):
                            rel_item = item.relative_to(src_pdir)
                            dst_item = cloud_pdir / rel_item
                            if item.is_dir():
                                dst_item.mkdir(parents=True, exist_ok=True)
                            elif item.is_file() and item.name != ".gitkeep":
                                dst_item.parent.mkdir(parents=True, exist_ok=True)
                                if not dst_item.exists():
                                    shutil.copy2(item, dst_item)

                src_wf = src_pdir / "workflows"
                if src_wf.exists():
                    for wf in src_wf.glob("*.json"):
                        dst_wf = cloud_pdir / "workflows" / wf.name
                        if not dst_wf.exists():
                            shutil.copy2(wf, dst_wf)
        print(f"[云端剧本项目就绪] {cloud_pdir}", flush=True)


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
        print(f"  [警告] 无法列出仓库 {repo_id} 文件列表 ({exc})，将直接尝试精确路径。", flush=True)
        return preferred_path

    if preferred_path in files:
        return preferred_path

    if fallback_keywords:
        lowered = [kw.lower() for kw in fallback_keywords]
        excluded = [kw.lower() for kw in exclude_keywords]
        candidates = [
            f
            for f in files
            if all(kw in f.lower() for kw in lowered) and not any(ex in f.lower() for ex in excluded)
        ]
        if len(candidates) == 1:
            print(f"  [自动修正路径] {preferred_path} -> {candidates[0]}", flush=True)
            return candidates[0]
        if len(candidates) > 1:
            candidates.sort(key=len)
            print(f"  [自动修正路径] 匹配到多个候选，选用最短路径: {candidates[0]}", flush=True)
            return candidates[0]

    raise FileNotFoundError(
        f"仓库 {repo_id} 中未找到 {preferred_path}（关键词 {fallback_keywords} 也无匹配）。"
        f"请检查模型仓库或更新 configs/models_manifest.json。"
    )


def resolve_remote_file_meta(
    api: Any,
    repo_id: str,
    repo_path: str,
    token: str | None,
) -> tuple[int | None, str | None]:
    """从 Hugging Face API 获取文件精确字节数与 LFS SHA256（用于精确跳过与落地防损校验）。"""
    try:
        infos = api.get_paths_info(repo_id=repo_id, paths=[repo_path], token=token)
        if infos:
            info = infos[0]
            size = getattr(info, "size", None)
            lfs = getattr(info, "lfs", None)
            sha256: str | None = None
            if lfs is not None:
                sha256 = getattr(lfs, "sha256", None) or (lfs.get("sha256") if isinstance(lfs, dict) else None)
                if not size:
                    size = getattr(lfs, "size", None) or (lfs.get("size") if isinstance(lfs, dict) else None)
            return (int(size) if size else None), (str(sha256) if sha256 else None)
    except Exception as exc:
        print(f"  [提示] 获取远端元信息失败 ({repo_path}: {exc})，将由传输层自动探测大小。", flush=True)
    return None, None


def cleanup_stale_tmp() -> None:
    """清理 /tmp 下残留的下载缓存，防止占满 Colab 107GB 本地根磁盘。"""
    tmp_root = Path(tempfile.gettempdir())
    for p in list(tmp_root.glob("hf_dl_*")) + [tmp_root / "huggingface"]:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def _is_size_valid(file_path: Path, expected_size: int | None) -> bool:
    if not file_path.exists():
        return False
    actual = file_path.stat().st_size
    if expected_size and expected_size > 0:
        return actual == expected_size
    return actual > 1024 * 1024


def download_file_via_drivefs(
    *,
    entry: dict[str, Any],
    repo_id: str,
    repo_path: str,
    expected_size: int | None,
    drive_models_root: Path,
    token: str | None,
    force: bool = False,
) -> None:
    """优化后的 DriveFS 回退通道：顺序写分片 + 256MB 磁盘缓冲 + 精确字节数校验。"""
    from huggingface_hub import hf_hub_download

    cleanup_stale_tmp()
    target_dir = drive_models_root / entry["target_subdir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / entry["filename"]

    if not force and _is_size_valid(final_path, expected_size):
        size_gb = final_path.stat().st_size / (1024 ** 3)
        print(f"  [已存在跳过] {entry['target_subdir']}/{entry['filename']} ({size_gb:.2f} GB)", flush=True)
        return

    print(f"  [DriveFS 顺序直写] {repo_id} :: {repo_path}", flush=True)
    t0 = time.time()
    hf_url = f"https://huggingface.co/{repo_id}/resolve/main/{repo_path}"
    has_aria2 = shutil.which("aria2c") is not None
    tmp_drive_path = final_path.with_suffix(final_path.suffix + ".part")

    # 中小文件（本地可用空间充足且 < 35GB）优先走 hf_xet/hf_hub_download 落 /tmp 再 16MB 大块顺序写入 Drive
    free_tmp_bytes = shutil.disk_usage(tempfile.gettempdir()).free
    prefer_local_stage = (
        expected_size is not None
        and expected_size <= 35 * (1024 ** 3)
        and free_tmp_bytes >= expected_size * 2.3
    )

    used_aria2 = False
    if has_aria2 and not prefer_local_stage:
        aria_cmd = [
            "aria2c",
            "-x", "8",
            "-s", "8",
            "-k", "64M",
            "--stream-piece-selector=inorder",
            "--disk-cache=256M",
            "--file-allocation=none",
            "--continue=true",
            "--console-log-level=warn",
            "--summary-interval=30",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "-d", str(target_dir),
            "-o", tmp_drive_path.name,
        ]
        if token:
            aria_cmd.extend(["--header", f"Authorization: Bearer {token}"])
        aria_cmd.append(hf_url)
        res = subprocess.run(aria_cmd)
        if res.returncode == 0 and _is_size_valid(tmp_drive_path, expected_size):
            os.replace(tmp_drive_path, final_path)
            used_aria2 = True
        else:
            print("  [回退] aria2c 直写未通过完整性校验，切换 hf_hub_download...", flush=True)

    if not used_aria2:
        if tmp_drive_path.exists():
            tmp_drive_path.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix="hf_dl_") as tmp_dir:
            local_cached = Path(
                hf_hub_download(
                    repo_id=repo_id,
                    filename=repo_path,
                    local_dir=tmp_dir,
                    token=token,
                )
            )
            if not _is_size_valid(local_cached, expected_size):
                raise RuntimeError(f"hf_hub_download 大小校验失败: {local_cached}")
            copy_file_fast(local_cached, final_path)

    cleanup_stale_tmp()
    elapsed = time.time() - t0
    size_gb = final_path.stat().st_size / (1024 ** 3)
    speed_mb = (final_path.stat().st_size / (1024 ** 2)) / max(elapsed, 0.1)
    print(f"  [同步完成] {final_path} ({size_gb:.2f} GB, 总耗时 {elapsed:.1f}s, ~{speed_mb:.1f} MB/s)", flush=True)


def sync_single_entry(
    *,
    entry: dict[str, Any],
    drive_models_root: Path,
    drive_models_rel_parts: list[str] | None,
    drive_client: GoogleDriveClient | None,
    token: str | None,
    force: bool,
    upload_chunk_mb: int,
    fetch_workers: int,
) -> dict[str, Any]:
    from huggingface_hub import HfApi

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
    expected_size, expected_sha256 = resolve_remote_file_meta(api, repo_id, repo_path, token)
    hf_url = f"https://huggingface.co/{repo_id}/resolve/main/{repo_path}"

    if drive_client is not None and drive_models_rel_parts is not None:
        folder_parts = [*drive_models_rel_parts, entry["target_subdir"]]
        source_headers = {"Authorization": f"Bearer {token}"} if token else None
        size_hint = f"{expected_size / (1024 ** 3):.2f} GB" if expected_size else "探测中"
        print(
            f"  [API流水线直传] {repo_id} :: {repo_path} ({size_hint}, chunk={upload_chunk_mb}MiB, fetch={fetch_workers}线程)",
            flush=True,
        )
        return drive_client.stream_url_to_drive(
            source_url=hf_url,
            folder_parts=folder_parts,
            filename=entry["filename"],
            expected_size=expected_size,
            expected_sha256=expected_sha256,
            source_headers=source_headers,
            force=force,
            upload_chunk_mb=upload_chunk_mb,
            fetch_workers=fetch_workers,
        )

    download_file_via_drivefs(
        entry=entry,
        repo_id=repo_id,
        repo_path=repo_path,
        expected_size=expected_size,
        drive_models_root=drive_models_root,
        token=token,
        force=force,
    )
    return {"status": "drivefs_done"}


def main() -> int:
    parser = argparse.ArgumentParser(description="将开源视频模型包与剧本项目结构高速同步到 Google Drive 5TB")
    parser.add_argument("--manifest", default="configs/models_manifest.json", help="模型清单路径")
    parser.add_argument("--repo-root", default=".", help="AI-Video 仓库根目录（用于同步 projects/ 剧本项目上云）")
    parser.add_argument("--project", default="01_rainy_signal", help="同步初始化的剧本项目 ID")
    parser.add_argument("--drive-root", default=None, help="Google Drive 项目根目录")
    parser.add_argument("--packs", nargs="+", required=True, help="要同步的模型包 ID 列表，或传 all")
    parser.add_argument("--hf-token", default=os.environ.get("HF_TOKEN"), help="Hugging Face Token（可选，避免共享 IP 限流）")
    parser.add_argument(
        "--transfer-mode",
        choices=["auto", "drive_api", "drivefs"],
        default="auto",
        help="传输引擎：auto(优先 Drive API 零落盘直传，失败自动回退 DriveFS) / drive_api / drivefs",
    )
    parser.add_argument("--file-workers", type=int, default=3, help="Drive API 模式下并发直传的文件数量（默认 3，实测聚合吞吐 2.5x+）")
    parser.add_argument(
        "--fetch-workers",
        type=int,
        default=DEFAULT_FETCH_WORKERS,
        help="单文件从 Hugging Face 拉取分片的并发连接数（默认 8）",
    )
    parser.add_argument(
        "--upload-chunk-mb",
        type=int,
        default=DEFAULT_UPLOAD_CHUNK_MB,
        help="Google Drive Resumable Upload 单块大小 MiB（默认 256，实测追平单流上限）",
    )
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
    drive_models_rel_parts = drive_path_to_rel_parts(drive_models_root)

    drive_client: GoogleDriveClient | None = None
    if args.transfer_mode in ("auto", "drive_api"):
        if drive_models_rel_parts is None:
            if args.transfer_mode == "drive_api":
                print(
                    f"[错误] --drive-root={drive_root} 不包含 /MyDrive/，无法映射为 Google Drive v3 API 目录。",
                    file=sys.stderr,
                )
                return 1
            print(f"[提示] {drive_root} 非标准 /MyDrive/ 挂载路径，将使用 DriveFS 模式。", flush=True)
        else:
            drive_client = try_create_drive_client(verbose=True)
            if drive_client is None and args.transfer_mode == "drive_api":
                print(
                    "[错误] 已指定 --transfer-mode=drive_api，但未检测到有效的 Google OAuth 凭证。"
                    "请先在 Colab 执行 auth.authenticate_user()。",
                    file=sys.stderr,
                )
                return 1

    selected = list(packs_cfg.keys()) if "all" in args.packs else args.packs
    for pid in selected:
        if pid not in packs_cfg:
            print(f"[错误] 未知模型包: {pid}。可选: {', '.join(packs_cfg.keys())}", file=sys.stderr)
            return 1

    # 按 (target_subdir, filename) 去重收集所有待同步文件
    dedup_entries: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for pid in selected:
        pack = packs_cfg[pid]
        print(f"\n=== 计划同步模型包: {pid} ({pack['label']}, 约 {pack['estimated_gb']} GB) ===", flush=True)
        if pack.get("requires_hf_token") and not args.hf_token:
            print(
                f"  [跳过] {pid} 需要 HF_TOKEN，请先在 Hugging Face 同意协议并通过 --hf-token 或环境变量 HF_TOKEN 传入。",
                file=sys.stderr,
            )
            continue
        for entry in pack["files"]:
            key = (entry["target_subdir"], entry["filename"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            dedup_entries.append(entry)

    if not dedup_entries:
        print("\n[完成] 无需同步的模型文件。", flush=True)
        return 0

    t_all = time.time()
    if drive_client is not None and args.file_workers > 1 and len(dedup_entries) > 1:
        max_workers = min(max(1, args.file_workers), len(dedup_entries))
        print(
            f"\n[并发直传启动] 共 {len(dedup_entries)} 个独立权重文件，启用 {max_workers} 路并发 Google Drive v3 API 流水线...",
            flush=True,
        )
        errors: list[tuple[str, Exception]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            fut_map = {
                pool.submit(
                    sync_single_entry,
                    entry=entry,
                    drive_models_root=drive_models_root,
                    drive_models_rel_parts=drive_models_rel_parts,
                    drive_client=drive_client,
                    token=args.hf_token,
                    force=args.force,
                    upload_chunk_mb=args.upload_chunk_mb,
                    fetch_workers=args.fetch_workers,
                ): entry["filename"]
                for entry in dedup_entries
            }
            for fut in concurrent.futures.as_completed(fut_map):
                fname = fut_map[fut]
                try:
                    fut.result()
                except Exception as exc:
                    print(f"  [失败] {fname}: {exc}", file=sys.stderr, flush=True)
                    errors.append((fname, exc))
        if errors:
            print(f"\n[错误] 共 {len(errors)} 个文件同步失败。", file=sys.stderr)
            return 1
    else:
        for entry in dedup_entries:
            sync_single_entry(
                entry=entry,
                drive_models_root=drive_models_root,
                drive_models_rel_parts=drive_models_rel_parts,
                drive_client=drive_client,
                token=args.hf_token,
                force=args.force,
                upload_chunk_mb=args.upload_chunk_mb,
                fetch_workers=args.fetch_workers,
            )

    print(
        f"\n[全部完成] 模型资源与剧本项目已存入 5TB Google Drive（总耗时 {time.time() - t_all:.1f}s），"
        "可切换至 A100 运行时直接生成！",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
