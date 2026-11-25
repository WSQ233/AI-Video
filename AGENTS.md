# AGENTS.md — AI-Video 项目工程与协作规范

本文件为所有 AI Agent 与开发者在 `WSQ233/AI-Video`（本地路径 `D:\AI\AI-Video`）中的强制执行规范。任何新增脚本、模型配置、剧本或 Notebook 均必须严格遵守以下条款。

---

## 1. 沟通与文档语言
- **全程使用中文**：对外回复、架构文档、Notebook 表单说明、脚本注释与运行日志均默认使用简洁准确的中文（代码标识符、CLI 参数与英文 Prompt 除外）。

---

## 2. 硬件资源与算力红线（不可违背）
- **云端存储**：Google AI Pro **5TB Google Drive**（根目录 `/MyDrive/AI_Video/`）。
- **核心算力**：Google Colab **A100 80GB** 计算单元 + **免费 CPU** 运行时。
- **零浪费 CU 原则**：
  1. **下载/同步模型、初始化云盘目录**：必须使用 **免费 CPU（0 CU）** 运行 `notebooks/00_sync_models_to_drive.ipynb`，禁止为下载模型开启 GPU。
  2. **批量出片自动止损**：`notebooks/02_h100_batch_runner.ipynb` 默认开启 `AUTO_DISCONNECT = True`，任务完成并 `sync` 落盘后自动调用 `runtime.unassign()` 释放 A100。
- **A100 80GB 显存与本地盘红线**：
  1. ComfyUI 启动必须使用 **`--normalvram --bf16-vae`**（禁止使用 `--highvram`，否则 27GB Qwen3-VL + 61.7GB 33.1B BF16 同时驻留会直接撑爆 80GB 显存）。
  2. Colab 本地临时盘仅 ~235GB：**每次启动只预热当前任务需要的 1 个主模型包（~95GB）到本地 NVMe SSD**，严禁同时把 `FL2VA BF16` 与 `Ref2VA BF16` 两套 61.7GB 主权重一起拷进 `/content`；其余权重通过 `extra_model_paths.yaml` 从 5TB Drive 兜底发现。

---

## 3. 模型选型规范
- **唯一主力引擎**：**MiniMax H3（`Comfy-Org/MiniMax-H3` · 33.1B 全参数未剪枝无损版）**
  - 主模型：`minimax_h3_fl2va_bf16.safetensors`（61.7GB）、`minimax_h3_ref2va_bf16.safetensors`（61.7GB）
  - 文本/多模态编码器：`qwen3vl_32b_minimax_h3_int8_convrot.safetensors`（27.1GB）
  - 音视频双 VAE：`minimax_h3_video_vae_fp16.safetensors` + `minimax_h3_audio_vae_fp32.safetensors`
  - 加速 LoRA：`lightx2v/Minimax-h3-Turbo`（日常快速验证用 4–8 步，终稿精渲可关闭走满步数）
  - 长片高显存余量备选：仅允许使用 **33.1B 未剪枝 `int8_convrot`**（~31.7GB）。
- **明确禁止项**：
  - **禁止默认引入或回退至 Wan 2.2**（除非用户明确提出）。
  - **禁止默认选用 20B 剪枝版（`pruned`）或低比特消费级 GGUF**；`configs/models_manifest.json` 与 `scripts/sync_models_to_drive.py` 中必须保留 `exclude_keywords: ["pruned"]` 防止路径自动匹配误下剪枝权重。

---

## 4. 全云端存储与「一剧本一项目」目录规范
- **所有重型资源必须放云端（5TB Google Drive）**：模型权重、参考图、参考音视频、成品视频、运行日志一律存于 `/MyDrive/AI_Video/`，本地电脑和 Git 仓库严禁存放大体积媒体或模型文件。
- **全局共享层 vs 独立项目层**：
  ```text
  /MyDrive/AI_Video/
  ├── shared/                        # 跨项目复用资产
  │   ├── models/                    # 全部共享模型权重
  │   ├── workflows/                 # 通用 ComfyUI API 工作流模板
  │   └── logs/                      # 系统级日志与冻结锁备份
  └── projects/                      # 一剧本一项目（含所有测试剧本）
      └── <project_id>/              # 如 01_rainy_signal
          ├── project.json           # 项目元配置
          ├── script.md              # 剧本、角色锚点与分镜 Prompt
          ├── tasks.csv              # 本项目批处理分镜清单
          ├── inputs/                # 本项目专属参考图/首尾帧/音频（直连 ComfyUI/input）
          ├── workflows/             # 本项目专属工作流（优先覆盖 shared/workflows）
          ├── outputs/               # 本项目生成视频与 manifest.jsonl（直连 ComfyUI/output）
          └── logs/                  # 本项目运行日志
  ```
- **创建新项目流程**：必须运行 `python scripts/new_project.py <project_id> "<项目标题>"`，禁止把散落的剧本或 CSV 直接堆在仓库根目录。

---

## 5. 工作流稳定性与环境锁定规范
- **极简插件原则**：MiniMax H3 直接使用 ComfyUI 原生加载，仅保留 `ComfyUI-Manager`、`ComfyUI-VideoHelperSuite`、`ComfyUI-KJNodes` 等必要节点，避免非必要第三方插件引发依赖冲突。
- **版本冻结**：在 Colab 确认首次全流程跑通后，运行 `scripts/freeze_locks.py` 导出精确 `git commit SHA` 并更新 `configs/nodes_lock.json`，确保后续每次重装 100% 可复现。
- **幂等与断点续传**：批处理脚本（`scripts/batch_runner.py`）必须基于 `task_id` 和项目目录下 `outputs/<batch>/manifest.jsonl` 实现自动跳过已完成任务与单条异常隔离，不得因单条失败中断整批队列。
- **模型写入原子性**：从 Hugging Face 或本地盘写入 5TB Google Drive 必须先写 `.part` 临时文件再 `os.replace()` 原子替换，防止网络中断留下损坏权重。

---

## 6. 代码安全、校验与 Git 提交流程
- **仓库信息**：`https://github.com/WSQ233/AI-Video.git`（分支 `main`，本地目录 `D:\AI\AI-Video`）。
- **严禁提交密钥**：禁止在任何代码、JSON 或 Notebook 中硬编码 `HF_TOKEN`、Google 凭证或密码；统一优先从 Colab Secrets (`google.colab.userdata`) 或环境变量读取。
- **提交前必须校验**：每次修改后、执行 `git commit` 前必须运行校验命令，确保所有 `.py` 编译通过、所有 `.json` 和 `.ipynb` 可正确解析、项目 `tasks.csv` 字段完整：
  ```powershell
  python -c "import json, py_compile, pathlib; root=pathlib.Path(r'D:\AI\AI-Video'); [py_compile.compile(str(p), doraise=True) for p in root.rglob('*.py')]; [json.loads(p.read_text(encoding='utf-8')) for p in list(root.rglob('*.json')) + list(root.rglob('*.ipynb'))]; print('ALL VALID OK')"
  ```
- **清晰的提交信息**：使用约定式提交前缀（`feat:` / `fix:` / `refactor:` / `chore:` / `docs:`），避免把 `__pycache__`、临时日志或大文件纳入版本控制。
