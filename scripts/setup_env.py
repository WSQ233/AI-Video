#!/usr/bin/env python3
"""
Colab GPU (H100 / A100 / L4) 一键装机与 Google Drive 剧本项目资产挂载脚本：
1. 克隆并锁定 ComfyUI 与精简自定义节点
2. 将当前剧本项目的 images/、characters/<character_id>/、outputs/、workflows/ 与 ComfyUI 直连
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


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def detect_gpu_tier() -> tuple[str, str]:
    """检测当前 GPU 型号与精确显存，自动区分 A100_40GB / A100_80GB / H100 / L4。"""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            text=True,
        ).strip()
    except Exception:
        return "DEFAULT", "No GPU detected"

    first_line = out.splitlines()[0]
    parts = [p.strip() for p in first_line.split(",")]
    name = parts[0] if parts else first_line
    vram_mb = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    display = f"{name} ({vram_mb / 1024:.1f} GB VRAM)" if vram_mb else name

    upper = name.upper()
    if "H100" in upper:
        return "H100", display
    if "A100" in upper:
        return ("A100_80GB" if vram_mb >= 65000 else "A100_40GB"), display
    if "L4" in upper:
        return "L4", display
    return "DEFAULT", display


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
        for item in link_path.iterdir():
            dst = target_path / item.name
            if not dst.exists():
                shutil.move(str(item), str(dst))
        shutil.rmtree(link_path)
    link_path.symlink_to(target_path, target_is_directory=True)
    print(f"  [软链接] {link_path} -> {target_path}")


def ensure_file_symlink(link_path: Path, target_file: Path) -> None:
    """在本地 ComfyUI/input 下为人物锚定图和图片资源创建便捷文件软链接，兼容相对路径与平铺文件名。"""
    if not target_file.is_file():
        return
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.is_symlink() or link_path.exists():
        try:
            if link_path.resolve() == target_file.resolve():
                return
        except Exception:
            pass
        if link_path.is_symlink() or link_path.is_file():
            link_path.unlink()
    link_path.symlink_to(target_file)


def mount_project_input_assets(comfy_input_dir: Path, project_dir: Path) -> None:
    """
    将剧本项目下的 images/（通用图片资源）与 characters/<character_id>/（人物形象独立目录）
    挂载到 ComfyUI/input 下：
    1. 支持 `characters/<character_id>/ref_xxx.png` 与 `images/xxx.png` 规范相对路径加载
    2. 自动将已有图片平铺软链接到 `ComfyUI/input/` 根目录，方便 WebUI 下拉框选择与旧版简写文件名兜底
    """
    if comfy_input_dir.is_symlink():
        comfy_input_dir.unlink()
    comfy_input_dir.mkdir(parents=True, exist_ok=True)

    for sub in ("images", "characters", "videos"):
        target_sub = project_dir / sub
        target_sub.mkdir(parents=True, exist_ok=True)
        ensure_symlink(comfy_input_dir / sub, target_sub)

    # 兼容旧版云盘上的 inputs/ 目录（如存在旧参考图，自动同步回 characters/ 或挂入 inputs 子链接）
    legacy_inputs = project_dir / "inputs"
    if legacy_inputs.exists() and legacy_inputs.is_dir():
        ensure_symlink(comfy_input_dir / "inputs", legacy_inputs)
        for img in legacy_inputs.iterdir():
            if img.is_file() and img.suffix.lower() in IMAGE_EXTENSIONS:
                ensure_file_symlink(comfy_input_dir / img.name, img)
                # 若是 ref_<character_id>.png 且对应人物文件夹存在但尚无该图，自动复制一份到人物独立目录
                if img.stem.startswith("ref_"):
                    cid = img.stem[len("ref_"):].split("_")[0]
                    char_dir = project_dir / "characters" / cid
                    if char_dir.is_dir() and not (char_dir / img.name).exists():
                        shutil.copy2(img, char_dir / img.name)
                        print(f"  [自动归档人物锚定图] {img.name} -> {char_dir / img.name}")

    # 为 characters/<character_id>/*、images/* 与 videos/* 下的媒体创建平铺软链接到 ComfyUI/input/
    for img in (project_dir / "characters").rglob("*"):
        if img.is_file() and img.suffix.lower() in IMAGE_EXTENSIONS:
            ensure_file_symlink(comfy_input_dir / img.name, img)
    for img in (project_dir / "images").rglob("*"):
        if img.is_file() and img.suffix.lower() in IMAGE_EXTENSIONS:
            ensure_file_symlink(comfy_input_dir / img.name, img)
    if (project_dir / "videos").exists():
        for vid in (project_dir / "videos").rglob("*"):
            if vid.is_file() and vid.suffix.lower() in VIDEO_EXTENSIONS:
                ensure_file_symlink(comfy_input_dir / vid.name, vid)


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
    shared_models_dir: Path,
    comfy_dir: Path,
    mode: str,
    workers: int,
) -> list[str]:
    """按选定 pack 将模型从 5TB Google Drive 共享模型库准备到本地 ComfyUI/models。"""
    drive_models = shared_models_dir
    local_models = comfy_dir / "models"
    missing: list[str] = []

    ensure_symlink(local_models / "loras", drive_models / "loras")

    if mode == "symlink":
        for sub in ["diffusion_models", "text_encoders", "vae", "upscale_models", "latent_upscale_models", "clip_vision"]:
            ensure_symlink(local_models / sub, drive_models / sub)
        return missing

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


def write_extra_model_paths(comfy_dir: Path, shared_models_dir: Path) -> None:
    """将 Google Drive 全局共享模型库注册为额外路径，方便临时切换未预拷的模型。"""
    yaml_content = f"""drive_5t_shared:
    base_path: {shared_models_dir}
    diffusion_models: diffusion_models/
    text_encoders: text_encoders/
    vae: vae/
    loras: loras/
    upscale_models: upscale_models/
    latent_upscale_models: latent_upscale_models/
    clip_vision: clip_vision/
"""
    (comfy_dir / "extra_model_paths.yaml").write_text(yaml_content, encoding="utf-8")


def sync_project_files_to_drive(repo_root: Path, shared_dir: Path, project_dir: Path, project_id: str) -> None:
    """确保共享层与剧本项目云端目录（原始剧本、分镜头剧本、图片、人物独立目录、工作流、产出视频）完整并同步。"""
    (shared_dir / "workflows").mkdir(parents=True, exist_ok=True)
    (shared_dir / "logs").mkdir(parents=True, exist_ok=True)
    for sub in (
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
    ):
        (project_dir / sub).mkdir(parents=True, exist_ok=True)

    src_pdir = repo_root / "projects" / project_id
    if src_pdir.exists():
        # 1. 同步剧本项目核心文档与任务表（project.json、原始剧本 source_script.md、分镜头剧本 storyboard.md、tasks.csv）
        for fname in ("project.json", "source_script.md", "storyboard.md", "tasks.csv", "script.md"):
            src = src_pdir / fname
            dst = project_dir / fname
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

        # 2. 同步剧本项目专属 ComfyUI 流程 (projects/<project_id>/workflows/*.json)
        src_wf_dir = src_pdir / "workflows"
        if src_wf_dir.exists():
            for wf in src_wf_dir.glob("*.json"):
                dst_wf = project_dir / "workflows" / wf.name
                if not dst_wf.exists():
                    shutil.copy2(wf, dst_wf)

        # 3. 递归同步人物独立目录（含 outfits/、voice/）、视觉场景/道具/关键帧目录 (images/*)、原视频参考目录 (videos/*) 与音频目录 (audio/*)
        for tree_sub in ("characters", "images", "videos", "audio"):
            src_tree = src_pdir / tree_sub
            if src_tree.exists():
                for item in src_tree.rglob("*"):
                    rel_item = item.relative_to(src_pdir)
                    dst_item = project_dir / rel_item
                    if item.is_dir():
                        dst_item.mkdir(parents=True, exist_ok=True)
                    elif item.is_file() and item.name != ".gitkeep":
                        dst_item.parent.mkdir(parents=True, exist_ok=True)
                        if not dst_item.exists():
                            shutil.copy2(item, dst_item)

    # 5. 共享工作流模板兜底补充
    repo_shared_wf = repo_root / "workflows" / "shared"
    if repo_shared_wf.exists():
        for wf in repo_shared_wf.glob("*.json"):
            for target_wf in (shared_dir / "workflows" / wf.name, project_dir / "workflows" / wf.name):
                if not target_wf.exists():
                    shutil.copy2(wf, target_wf)


def main() -> int:
    parser = argparse.ArgumentParser(description="Colab GPU ComfyUI 一键装机脚本（支持独立剧本项目挂载）")
    parser.add_argument("--repo-root", default=".", help="AI-Video 仓库根目录")
    parser.add_argument("--project", default=None, help="本次挂载的独立剧本项目 ID（如 01_rainy_signal）")
    parser.add_argument("--packs", nargs="*", default=None, help="本次预热的模型包 ID")
    parser.add_argument("--mode", choices=["copy_to_local", "symlink"], default=None, help="模型加载模式")
    parser.add_argument("--enable-ltx", action="store_true", help="强制启用 ComfyUI-LTXVideo 节点")
    parser.add_argument("--sageattention", action="store_true", help="安装 SageAttention 2.x (可选提速)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    profile = json.loads((repo_root / "configs/runtime_profile.json").read_text(encoding="utf-8"))
    nodes_lock = json.loads((repo_root / "configs/nodes_lock.json").read_text(encoding="utf-8"))
    manifest = json.loads((repo_root / "configs/models_manifest.json").read_text(encoding="utf-8"))

    drive_root = Path(profile["drive_root"])
    shared_dir = drive_root / profile.get("shared_subdir", "shared")
    shared_models_dir = shared_dir / "models"
    project_id = args.project or profile.get("default_project", "01_rainy_signal")
    project_dir = drive_root / "projects" / project_id
    comfy_dir = Path(profile["comfyui_dir"])
    packs = args.packs if args.packs else profile["default_packs"]
    mode = args.mode or profile.get("model_load_mode", "copy_to_local")
    workers = int(profile.get("copy_workers", 4))

    gpu_tier, gpu_raw = detect_gpu_tier()
    gpu_cfg = profile["gpu_profiles"].get(gpu_tier, profile["gpu_profiles"]["DEFAULT"])
    disk_free_gb = shutil.disk_usage("/content" if Path("/content").exists() else ".").free / (1024 ** 3)

    print("==========================================")
    print(f"GPU 检测       : {gpu_raw} -> 档位 [{gpu_tier}]")
    print(f"本地剩余磁盘   : {disk_free_gb:.1f} GB")
    print(f"云端共享模型库 : {shared_models_dir}")
    print(f"当前剧本项目   : {project_id} -> {project_dir}")
    print(f"启用模型包     : {', '.join(packs)} (模式: {mode})")
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
        if node["name"] == "ComfyUI-LTXVideo" and (args.enable_ltx or any(p.startswith("ltx25") for p in packs)):
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

    # 4. 初始化独立剧本项目云端目录并软链接直连 ComfyUI
    print(f"\n[剧本项目云端绑定] 将 ComfyUI 挂载到独立剧本项目: {project_dir}")
    sync_project_files_to_drive(repo_root, shared_dir, project_dir, project_id)
    mount_project_input_assets(comfy_dir / "input", project_dir)
    ensure_symlink(comfy_dir / "output", project_dir / "outputs")
    ensure_symlink(comfy_dir / "user" / "default" / "workflows", project_dir / "workflows")

    # 5. 准备共享模型权重 + 写 extra_model_paths.yaml
    missing = stage_models_from_drive(
        manifest=manifest,
        packs=packs,
        shared_models_dir=shared_models_dir,
        comfy_dir=comfy_dir,
        mode=mode,
        workers=workers,
    )
    write_extra_model_paths(comfy_dir, shared_models_dir)

    # 6. 写入本次启动参数供 Notebook 直接读取
    launch_info = {
        "gpu_tier": gpu_tier,
        "gpu_raw": gpu_raw,
        "project_id": project_id,
        "project_dir": str(project_dir),
        "shared_dir": str(shared_dir),
        "comfyui_dir": str(comfy_dir),
        "comfyui_args": gpu_cfg["comfyui_args"],
        "packs": packs,
        "missing_models": missing,
    }
    (comfy_dir / "launch_info.json").write_text(json.dumps(launch_info, ensure_ascii=False, indent=2), encoding="utf-8")

    if missing:
        print("\n[注意] 以下共享模型尚未在 5TB Google Drive 中找到，请先在免费 CPU 运行 00_sync_models_to_drive.ipynb 下载：")
        for m in missing:
            print(f"  - {m}")
    else:
        print("\n[预检通过] 所有选定模型包与独立剧本项目目录均已就绪！")

    print(f"[推荐启动参数] python main.py {gpu_cfg['comfyui_args']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
