#!/usr/bin/env python3
"""
项目级 Hook：当 AI-Video 的 Colab / ComfyUI 流程文件（configs、scripts、notebooks、workflows）
发生修改时，自动提取最新运行参数、模型包清单、脚本 CLI 接口、Notebook 表单参数与工作流占位符，
并同步更新 `.agents/skills/colab-comfyui-control/SKILL.md` 中的基线区块。

支持三种运行模式：
1. 直接运行：`python .agents/hooks/sync_colab_comfyui_skill.py`（立即同步 SKILL.md）
2. 校验模式：`python .agents/hooks/sync_colab_comfyui_skill.py --check`（校验 SKILL.md 是否与当前流程一致）
3. Hook 模式：`python .agents/hooks/sync_colab_comfyui_skill.py --hook`（兼容 Antigravity PostToolUse/Stop 与 Codex Stop 事件）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SKILL_REL_PATH = ".agents/skills/colab-comfyui-control/SKILL.md"
START_MARKER = "<!-- pipeline-baseline:begin -->"
END_MARKER = "<!-- pipeline-baseline:end -->"
STATE_RE = re.compile(r"<!-- pipeline-baseline:state ([a-f0-9]{64}) -->")

TRACKED_GLOBS = (
    "configs/*.json",
    "scripts/*.py",
    "notebooks/*.ipynb",
    "workflows/shared/*.json",
)


def collect_tracked_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in TRACKED_GLOBS:
        for p in root.glob(pattern):
            if p.is_file() and "__pycache__" not in p.parts:
                files.add(p)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def compute_source_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in collect_tracked_files(root):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"受监测的流程文件超出仓库根目录: {path}")
        rel = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(rel + b"\0" + hashlib.sha256(content).digest())
    return digest.hexdigest()


def extract_script_cli_flags(script_path: Path) -> list[str]:
    text = script_path.read_text(encoding="utf-8")
    return re.findall(r'add_argument\(\s*["\'](--[a-zA-Z0-9_-]+)["\']', text)


def extract_notebook_params(nb_path: Path) -> tuple[str, list[str]]:
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    title = nb_path.name
    params: list[str] = []
    seen: set[str] = set()
    for cell in nb.get("cells", []):
        lines = cell.get("source", [])
        if isinstance(lines, str):
            lines = lines.splitlines(keepends=True)
        if cell.get("cell_type") == "markdown" and title == nb_path.name:
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("# "):
                    title = stripped.lstrip("# ").strip()
                    break
        elif cell.get("cell_type") == "code":
            for line in lines:
                m = re.match(r"^([A-Z0-9_]+)\s*=\s*(.+?)\s*#@param", line.strip())
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    params.append(f"`{m.group(1)}={m.group(2)}`")
    return title, params


def extract_workflow_info(wf_path: Path) -> tuple[str, list[str]]:
    raw = wf_path.read_text(encoding="utf-8")
    obj = json.loads(raw)
    placeholders = sorted(set(re.findall(r"__[A-Z0-9_]+__", raw)))
    if "nodes" in obj and isinstance(obj["nodes"], list):
        kind = f"UI 工作流 ({len(obj['nodes'])} 节点)"
    else:
        node_types = [
            v.get("class_type", "")
            for v in obj.values()
            if isinstance(v, dict) and v.get("class_type")
        ]
        kind = f"API 工作流 ({len(node_types)} 节点)"
    return kind, placeholders


def build_baseline_markdown(root: Path) -> str:
    runtime_path = root / "configs/runtime_profile.json"
    manifest_path = root / "configs/models_manifest.json"
    nodes_path = root / "configs/nodes_lock.json"

    for req in (runtime_path, manifest_path, nodes_path):
        if not req.is_file():
            raise ValueError(f"缺少核心流程配置文件: {req.relative_to(root).as_posix()}")

    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    nodes_lock = json.loads(nodes_path.read_text(encoding="utf-8"))

    lines: list[str] = []

    # 1. 运行时与 GPU 档位基线
    lines.append("### 6.1 运行时配置与 GPU 档位 (`configs/runtime_profile.json`)")
    lines.append("")
    lines.append(
        f"- **云盘根目录**：`{runtime.get('drive_root')}` | **共享目录**：`{runtime.get('shared_subdir')}` | "
        f"**默认项目**：`{runtime.get('default_project')}` | **ComfyUI 目录**：`{runtime.get('comfyui_dir')}`"
    )
    lines.append(
        f"- **默认模型包**：{', '.join(f'`{p}`' for p in runtime.get('default_packs', []))} "
        f"（加载模式：`{runtime.get('model_load_mode')}`，并发线程：`{runtime.get('copy_workers')}`）"
    )
    lines.append("")
    lines.append("| GPU 档位 | ComfyUI 启动参数 (`comfyui_args`) | 推荐模型包 |")
    lines.append("| :--- | :--- | :--- |")
    for tier, cfg in runtime.get("gpu_profiles", {}).items():
        args_str = cfg.get("comfyui_args", "")
        rec_packs = ", ".join(f"`{p}`" for p in cfg.get("recommended_packs", []))
        lines.append(f"| `{tier}` | `{args_str}` | {rec_packs} |")

    # 2. 模型包清单基线
    lines.append("")
    lines.append("### 6.2 云端模型包清单 (`configs/models_manifest.json`)")
    lines.append("")
    lines.append("| 模型包 ID | 默认同步 | 包含权重文件（目标子目录/文件名） |")
    lines.append("| :--- | :--- | :--- |")
    for pack_id, pack in manifest.get("packs", {}).items():
        default_sync = "是" if pack.get("default_sync") else "否"
        files_desc = "<br/>".join(
            f"`{f.get('target_subdir')}/{f.get('filename')}` ({f.get('approx_gb')} GB)"
            for f in pack.get("files", [])
        )
        lines.append(f"| `{pack_id}` | {default_sync} | {files_desc} |")

    # 3. ComfyUI 与自定义节点锁定基线
    lines.append("")
    lines.append("### 6.3 ComfyUI 与自定义节点锁定 (`configs/nodes_lock.json`)")
    lines.append("")
    comfy_info = nodes_lock.get("comfyui", {})
    enabled_nodes = [
        f"`{n.get('name')}` (`{n.get('commit', 'HEAD')}`)"
        for n in nodes_lock.get("custom_nodes", [])
        if n.get("enabled")
    ]
    disabled_nodes = [
        f"`{n.get('name')}`"
        for n in nodes_lock.get("custom_nodes", [])
        if not n.get("enabled")
    ]
    lines.append(f"- **ComfyUI 核心**：`{comfy_info.get('repo')}` @ `{comfy_info.get('commit', 'HEAD')}`")
    lines.append(f"- **已启用节点**：{', '.join(enabled_nodes) if enabled_nodes else '无'}")
    lines.append(f"- **已禁用节点**：{', '.join(disabled_nodes) if disabled_nodes else '无'}")

    # 4. Colab Notebooks 与表单参数基线
    lines.append("")
    lines.append("### 6.4 Colab Notebooks 操控入口 (`notebooks/*.ipynb`)")
    lines.append("")
    lines.append("| Notebook 文件 | 标题与职责 | 暴露表单参数 (`#@param`) |")
    lines.append("| :--- | :--- | :--- |")
    for nb_path in sorted((root / "notebooks").glob("*.ipynb")):
        title, params = extract_notebook_params(nb_path)
        params_str = ", ".join(params) if params else "无"
        lines.append(f"| `{nb_path.relative_to(root).as_posix()}` | {title} | {params_str} |")

    # 5. 核心控制脚本 CLI 参数基线
    lines.append("")
    lines.append("### 6.5 控制脚本与 CLI 参数 (`scripts/*.py`)")
    lines.append("")
    lines.append("| 脚本路径 | 支持的 CLI 参数 |")
    lines.append("| :--- | :--- |")
    for script_path in sorted((root / "scripts").glob("*.py")):
        flags = extract_script_cli_flags(script_path)
        flags_str = ", ".join(f"`{fl}`" for fl in flags) if flags else "位置参数 / 无可选标志"
        lines.append(f"| `{script_path.relative_to(root).as_posix()}` | {flags_str} |")

    # 6. 共享工作流模板与占位符基线
    lines.append("")
    lines.append("### 6.6 共享 ComfyUI 工作流模板 (`workflows/shared/*.json`)")
    lines.append("")
    lines.append("| 工作流文件 | 类型与规模 | 动态替换占位符 |")
    lines.append("| :--- | :--- | :--- |")
    for wf_path in sorted((root / "workflows/shared").glob("*.json")):
        kind, placeholders = extract_workflow_info(wf_path)
        ph_str = ", ".join(f"`{ph}`" for ph in placeholders) if placeholders else "无（静态 UI 模板）"
        lines.append(f"| `{wf_path.relative_to(root).as_posix()}` | {kind} | {ph_str} |")

    return "\n".join(lines)


def render_skill(root: Path, original: str) -> str:
    if original.count(START_MARKER) != 1 or original.count(END_MARKER) != 1:
        raise ValueError(
            f"{SKILL_REL_PATH} 中的 {START_MARKER} 与 {END_MARKER} 起止标记必须各出现一次。"
        )
    before, _, tail = original.partition(START_MARKER)
    if END_MARKER not in tail:
        raise ValueError(f"{SKILL_REL_PATH} 中的 pipeline-baseline 起止标记顺序错误。")
    _, _, after = tail.partition(END_MARKER)

    digest = compute_source_digest(root)
    state_comment = f"<!-- pipeline-baseline:state {digest} -->"
    body = build_baseline_markdown(root)
    return f"{before}{START_MARKER}\n{state_comment}\n\n{body}\n\n{END_MARKER}{after}"


def sync_skill(root: Path, check: bool = False) -> bool:
    skill_path = root / SKILL_REL_PATH
    if not skill_path.is_file():
        raise ValueError(f"未找到项目级控制 Skill 文件: {SKILL_REL_PATH}")

    raw = skill_path.read_bytes()
    original = raw.decode("utf-8")
    begin, sep, rest = original.partition(START_MARKER)
    if not sep or END_MARKER not in rest:
        raise ValueError(
            f"{SKILL_REL_PATH} 中的 {START_MARKER} 与 {END_MARKER} 起止标记缺失或损坏。"
        )
    old_block, end, suffix = rest.partition(END_MARKER)
    newline = "\r\n" if "\r\n" in (old_block or original) else "\n"

    rendered = render_skill(root, original.replace("\r\n", "\n"))
    new_block = rendered.split(START_MARKER, 1)[1].split(END_MARKER, 1)[0].replace("\n", newline)
    updated = (begin + sep + new_block + end + suffix).encode("utf-8")

    if raw == updated:
        return False
    if check:
        raise ValueError(
            f"{SKILL_REL_PATH} 的流程基线有待同步，请运行 python .agents/hooks/sync_colab_comfyui_skill.py。"
        )

    fd, tmp_name = tempfile.mkstemp(dir=skill_path.parent, prefix=".skill-sync-")
    pending = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as tmp_fp:
            tmp_fp.write(updated)
        pending.chmod(skill_path.stat().st_mode)
        if raw != skill_path.read_bytes():
            raise ValueError(f"{SKILL_REL_PATH} 在同步期间被并发修改，请重试。")
        os.replace(pending, skill_path)
    finally:
        pending.unlink(missing_ok=True)
    return True


def handle_hook_invocation(root: Path) -> int:
    raw_stdin = sys.stdin.read().strip()
    event: dict[str, Any] = json.loads(raw_stdin) if raw_stdin else {}
    if not isinstance(event, dict):
        event = {}

    # 同时兼容 Antigravity (hookEventName / continuationActive) 与 Codex (hook_event_name / stop_hook_active)
    agy_event = event.get("hookEventName", "")
    codex_event = event.get("hook_event_name", "")
    event_name = agy_event or codex_event or "Stop"
    is_codex = bool(codex_event) and not bool(agy_event)
    retry = bool(event.get("continuationActive") or event.get("stop_hook_active"))

    try:
        changed = sync_skill(root, check=False)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        if event_name == "PostToolUse":
            # PostToolUse 契约要求输出空对象 {}
            print(json.dumps({}))
            return 0
        if is_codex:
            resp = {"systemMessage": str(error)} if retry else {"decision": "block", "reason": str(error)}
        else:
            resp = (
                {"decision": "allow"}
                if retry
                else {"decision": "continue", "reason": f"[Skill Sync Hook] {error}"}
            )
        print(json.dumps(resp, ensure_ascii=False))
        return 0

    if event_name == "PostToolUse":
        print(json.dumps({}))
        return 0

    if is_codex:
        print(
            json.dumps(
                {"systemMessage": f"已自动同步 {SKILL_REL_PATH} 流程基线。"} if changed else {},
                ensure_ascii=False,
            )
        )
    else:
        # Antigravity Stop 契约：返回非 "continue" 的 decision 允许正常结束回合
        print(json.dumps({"decision": "allow"}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="仅校验 SKILL.md 是否与当前流程文件同步")
    mode.add_argument("--hook", action="store_true", help="以生命周期 Hook 模式运行（读取 stdin JSON）")
    args = parser.parse_args()

    if args.hook:
        return handle_hook_invocation(ROOT)

    try:
        changed = sync_skill(ROOT, check=args.check)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        return 1

    print(
        f"{SKILL_REL_PATH} 已同步更新。"
        if changed
        else f"{SKILL_REL_PATH} 与当前流程配置一致。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
