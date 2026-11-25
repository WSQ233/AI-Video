#!/usr/bin/env python3
"""
Colab GPU (H100 / A100 / L4) 一键装机与 Google Drive 资产挂载脚本：
1. 克隆并锁定 ComfyUI 与精简自定义节点
2. 将 input / output / workflows / loras 软链接直连 5TB Google Drive（实时持久化，断线不丢）
3. 将本次启用的大模型包从 Google Drive 并行拷贝到 Colab 本地高速 SSD（避免 FUSE 读取卡顿）
4. 自动生成 extra_model_paths.yaml 兜底发现 Drive 全量模型，并输出环境预检报告
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def detect_gpu_tier() -> tuple[str, str]:
    """检测当前 GPU 型号并映射到 runtime_profile 档位。"""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            text=True,
        ).strip()
    except Exception:
        return "DEFAULT", "No GPU detected"

    upper = out.upper()
    if "H100" in upper:
        return "H100", out
    if "A100" in upper:
        return "A100", out
    if "L4" in upper:
        return "L4", out
    return "DEFAULT", out


def clone_or_checkout(repo_url: str, dest: Path, commit: str = "HEAD") -> None:
    if not dest.exists():
        run_cmd(["git", "clone", "--depth", "1", repo_url, str(dest)])
    if commit and commit != "HEAD":
        run_cmd(["git", "fetch", "--depth", "1", "origin", commit], cwd=dest, check=False)
        run_cmd(["git", "checkout", commit], cwd=dest)


def ensure_symlink(link_path: Path, target_path: Path) -> None:
    """安全创建目录软链接：如已存在空目录/旧链接则先清理。"""
    target_path.mkdir(parents=True, exist_ok=True)
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.is_symlink():
        if link_path.resolve() == target_path.resolve():
            return
        link_path.unlink()
    elif link_path.exists():
        # 迁移原目录中已有默认文件后再替换为软链接
        for item in link_path.iterdir():
            dst = target_path / item.name
            if not dst.exists():
                shutil.move(str(item), str(dst))
        shutil.rmtree(link_path)
    link_path.symlink_to(target_path, target_is_directory=True)
    print(f"  [软链接] {link_path} -> {target_path}")


def copy_one_file(src: Path, dst: Path) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size == src.stat().st_size:
        return f"跳过(本地已有): {dst.name}"
    t0 = time.time()
    tmp = dst.with_suffix(dst.suffix + ".part")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)
    gb = dst.stat().st_size / (1024 ** 3)
    dt = time.time() - t0
    return f"已拷入本地SSD: {dst.name} ({gb:.2f} GB, {dt:.1f}s)"


def stage_models_from_drive(
    manifest: dict[str, Any],
    packs: list[str],
    drive_root: Path,
    comfy_dir: Path,
    mode: str,
    workers: int,
) -> list[str]:
    """按选定 pack 将模型从 5TB Google Drive 准备到本地 ComfyUI/models。"""
    drive_models = drive_root / "models"
    local_models = comfy_dir / "models"
    missing: list[str] = []

    # LoRA 体积小且变动频繁，始终软链接直连 Drive
    ensure_symlink(local_models / "loras", drive_models / "loras")

    if mode == "symlink":
        for sub in ["diffusion_models", "text_encoders", "vae", "upscale_models", "latent_upscale_models", "clip_vision"]:
            ensure_symlink(local_models / sub, drive_models / sub)
        return missing

    # copy_to_local 模式：仅并行拷贝本次勾选 pack 的权重文件到高速本地盘
    jobs: list[tuple[Path, Path]] = []
    seen: set[tuple[str, str]] = set()
    for pid in packs:
        pack = manifest["packs"].get(pid)
        if not pack:
            print(f"[警告] 忽略未知 pack: {pid}")
            continue
        for entry in pack["files"]:
            sub = entry["target_subdir"]
            fname = entry["filename"]
            if sub == "loras":
                if not (drive_models / sub / fname).exists():
                    missing.append(f"{sub}/{fname}")
                continue
            key = (sub, fname)
            if key in seen:
                continue
            seen.add(key)
            src = drive_models / sub / fname
            dst = local_models / sub / fname
            if not src.exists():
                missing.append(f"{sub}/{fname}")
                continue
            jobs.append((src, dst))

    if jobs:
        print(f"\n[高速预热] 并行拷入 {len(jobs)} 个模型文件到 Colab 本地 SSD (workers={workers})...")
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            for msg in ex.map(lambda p: copy_one_file(p[0], p[1]), jobs):
                print(f"  {msg}")
        print(f"[预热完成] 总耗时 {time.time() - t0:.1f}s")

    return missing


def write_extra_model_paths(comfy_dir: Path, drive_root: Path) -> None:
    """将 Google Drive 全量模型目录注册为额外路径，方便临时切换未预拷的模型。"""
    yaml_content = f"""drive_5t:
    base_path: {drive_root / 'models'}
    diffusion_models: diffusion_models/
    text_encoders: text_encoders/
    vae: vae/
    loras: loras/
    upscale_models: upscale_models/
    latent_upscale_models: latent_upscale_models/
    clip_vision: clip_vision/
"""
    (comfy_dir / "extra_model_paths.yaml").write_text(yaml_content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Colab H100 ComfyUI 一键装机脚本")
    parser.add_argument("--repo-root", default=".", help="AI-Video 仓库根目录")
    parser.add_argument("--packs", nargs="*", default=None, help="本次预热的模型包 ID")
    parser.add_argument("--mode", choices=["copy_to_local", "symlink"], default=None, help="模型加载模式")
    parser.add_argument("--enable-ltx", action="store_true", help="强制启用 ComfyUI-LTXVideo 节点")
    parser.add_argument("--sageattention", action="store_true", help="安装 SageAttention 2.x (H100 可选极致提速)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    profile = json.loads((repo_root / "configs/runtime_profile.json").read_text(encoding="utf-8"))
    nodes_lock = json.loads((repo_root / "configs/nodes_lock.json").read_text(encoding="utf-8"))
    manifest = json.loads((repo_root / "configs/models_manifest.json").read_text(encoding="utf-8"))

    drive_root = Path(profile["drive_root"])
    comfy_dir = Path(profile["comfyui_dir"])
    packs = args.packs if args.packs else profile["default_packs"]
    mode = args.mode or profile.get("model_load_mode", "copy_to_local")
    workers = int(profile.get("copy_workers", 4))

    gpu_tier, gpu_raw = detect_gpu_tier()
    gpu_cfg = profile["gpu_profiles"].get(gpu_tier, profile["gpu_profiles"]["DEFAULT"])
    disk_free_gb = shutil.disk_usage("/content" if Path("/content").exists() else ".").free / (1024 ** 3)

    print("==========================================")
    print(f"GPU 检测     : {gpu_raw} -> 档位 [{gpu_tier}]")
    print(f"本地剩余磁盘 : {disk_free_gb:.1f} GB")
    print(f"Drive 根目录 : {drive_root}")
    print(f"启用模型包   : {', '.join(packs)} (模式: {mode})")
    print("==========================================")

    # 1. 安装 ComfyUI 核心
    clone_or_checkout(
        nodes_lock["comfyui"]["repo"],
        comfy_dir,
        nodes_lock["comfyui"].get("commit", "HEAD"),
    )
    run_cmd([sys.executable, "-m", "pip", "install", "-q", "-r", str(comfy_dir / "requirements.txt")])
    run_cmd([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub[hf_transfer]", "imageio-ffmpeg"])

    # 2. 安装精简自定义节点
    custom_nodes_dir = comfy_dir / "custom_nodes"
    custom_nodes_dir.mkdir(parents=True, exist_ok=True)
    for node in nodes_lock["custom_nodes"]:
        enabled = bool(node.get("enabled", False))
        if node["name"] == "ComfyUI-LTXVideo" and (args.enable_ltx or "ltx25_av" in packs):
            enabled = True
        if not enabled:
            continue
        node_dir = custom_nodes_dir / node["name"]
        clone_or_checkout(node["repo"], node_dir, node.get("commit", "HEAD"))
        req = node_dir / "requirements.txt"
        if req.exists():
            run_cmd([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)], check=False)

    # 3. 可选安装 SageAttention
    if args.sageattention or gpu_cfg.get("install_sageattention", False):
        print("[可选加速] 正在安装 SageAttention...")
        run_cmd([sys.executable, "-m", "pip", "install", "-q", "sageattention>=2.2.0"], check=False)

    # 4. 持久化目录软链接直连 5TB Google Drive
    print("\n[持久化绑定] 绑定输入/输出/工作流到 5TB Google Drive...")
    ensure_symlink(comfy_dir / "input", drive_root / "inputs")
    ensure_symlink(comfy_dir / "output", drive_root / "outputs")
    ensure_symlink(comfy_dir / "user" / "default" / "workflows", drive_root / "workflows")

    # 5. 准备模型权重 + 写 extra_model_paths.yaml
    missing = stage_models_from_drive(
        manifest=manifest,
        packs=packs,
        drive_root=drive_root,
        comfy_dir=comfy_dir,
        mode=mode,
        workers=workers,
    )
    write_extra_model_paths(comfy_dir, drive_root)

    # 6. 写入本次启动参数供 Notebook 直接读取
    launch_info = {
        "gpu_tier": gpu_tier,
        "gpu_raw": gpu_raw,
        "comfyui_dir": str(comfy_dir),
        "comfyui_args": gpu_cfg["comfyui_args"],
        "packs": packs,
        "missing_models": missing,
    }
    (comfy_dir / "launch_info.json").write_text(json.dumps(launch_info, ensure_ascii=False, indent=2), encoding="utf-8")

    if missing:
        print("\n[注意] 以下模型文件尚未在 Google Drive 中找到，请先在免费 CPU 运行 00_sync_models_to_drive.ipynb 下载：")
        for m in missing:
            print(f"  - {m}")
    else:
        print("\n[预检通过] 所有选定模型包均已就绪！")

    print(f"[推荐启动参数] python main.py {gpu_cfg['comfyui_args']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
