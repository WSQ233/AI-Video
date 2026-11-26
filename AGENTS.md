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
- **A100 显存、系统内存与本地盘红线**：
  1. ComfyUI（`v0.46.0+` 默认启用 `NORMAL_VRAM` 与 `comfy-aimdo DynamicVRAM`）启动必须使用 **`--bf16-vae --cache-none`**（严禁传入已废弃的 `--normalvram`，更严禁使用 `--highvram`；`--cache-none` 可确保 25.3GB `Qwen3-VL` 完成文本编码后立即从系统内存释放，避免与 61.7GB 33.1B BF16 主模型叠加撑爆 83.5GB 系统内存）。
  2. Colab 本地临时盘仅 ~235GB（且 DriveFS 读取时会在本地 `/` 产生数十 GB 缓存）：**每次启动只预热当前任务需要的 1 个主模型包（~95GB）到本地 NVMe SSD**，严禁同时把 `FL2VA BF16` 与 `Ref2VA BF16` 两套 61.7GB 主权重一起拷进 `/content`；其余权重通过 `extra_model_paths.yaml` 从 5TB Drive 兜底发现。

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

---

## 7. 调用与控制 Colab 及 ComfyUI 的注意事项（Skill 与 Hook 联动规范）

1. **必须先加载项目级控制 Skill**：
   - 凡涉及通过浏览器或 MCP 控制 Google Colab、处理 Google Drive 挂载授权、部署/启动 ComfyUI、执行 `MiniMax H3` 推理或排查 OOM 的任务，必须先读取并严格遵循项目级技能 [`.agents/skills/colab-comfyui-control/SKILL.md`](./.agents/skills/colab-comfyui-control/SKILL.md)。
2. **MCP 通道与账号绑定注意事项**：
   - **强制使用宿主 Chrome DevTools MCP**：必须通过 `chrome-devtools-plugin_chrome-devtools`（`--autoConnect` 直连宿主已登录 Chrome）操控 Colab，**严禁使用内置隔离 `browser` 子代理操作 Colab**（会被 Google OAuth 弹窗的 COOP 策略与跨域 `colab.googleusercontent.com` 输出沙箱拦截）。
   - **强制绑定 `?authuser=1`**：打开任何 Colab Notebook 链接必须显式带 `?authuser=1`（对应拥有 Colab Pro 计算单元与 5TB 云盘的 `wangsongqi233@gmail.com`），运行前核对页面右上角账号与运行时类型（下载模型用免费 CPU，渲染视频用 A100 高 RAM）。
   - **OAuth 弹窗接管与重跑自愈**：执行 `drive.mount('/content/drive')` 触发 Google 授权弹窗时，用 `list_pages` 定位 `accounts.google.com` 标签页并点击目标账号与两次「继续/允许」；若首次授权耗时导致单元格挂载超时，直接重跑该单元格即可秒级挂载。
3. **Colab 单元格与 ComfyUI 操控注意事项**：
   - **Monaco 编辑器注入**：修改表单单元格（`cellView: "form"`）代码时，先点击 `显示代码`，再通过 `evaluate_script` 调用 `window.monaco.editor.getModels()[i].setValue(...)` 整块注入，禁止用模拟按键逐字输入长代码。
   - **长耗时阶段定时轮询**：模型同步（`aria2c` 16 线程直写云盘 `.part`）、本地 SSD 预热（`copy_to_local`）及 8 步扩散采样期间，必须使用 `schedule`（60~180 秒间隔）配合 `take_snapshot` 检查进度，严禁死循环高频轮询。
   - **音视频参数与双流验收**：ComfyUI 原生 `MiniMaxH3ImageToVideo` / `MiniMaxH3ReferenceToVideo` 分辨率必须为 **32 的倍数**（标准 768p 为 `1344×768`），帧数必须满足 24fps 下 **`17k + 5` 时间网格**（`124` 帧 = 5.17s，`243` 帧 = 10.1s）；出片后必须用 `ffprobe` 校验同时存在 `h264` 视频流与 `32000 Hz` 双声道 `aac` 音频流。
   - **离线预览与防烧卡释放**：在线调试期间可将 Cell 3 的 `AUTO_DISCONNECT` 临时设为 `False`；一旦出片验收完成，必须将视频以 Base64 `<video controls autoplay loop>` 内嵌至单元格输出、执行 `sync` 刷盘，并立即调用 `runtime.unassign()` 释放 A100 计算单元。
4. **流程修改与项目级 Hook 自动同步规范**：
   - 本项目已配置项目级生命周期 Hook（Antigravity [`.agents/hooks.json`](./.agents/hooks.json) 与 Codex [`.codex/hooks.json`](./.codex/hooks.json)，执行脚本为 [`.agents/hooks/sync_colab_comfyui_skill.py`](./.agents/hooks/sync_colab_comfyui_skill.py)）。
   - 每当修改 `configs/*.json`、`scripts/*.py`、`notebooks/*.ipynb` 或 `workflows/shared/*.json` 时，Hook 会在工具执行后（`PostToolUse`）与回合结束时（`Stop`）自动提取最新配置、CLI 参数、Notebook 表单字段及工作流占位符，同步更新 [`.agents/skills/colab-comfyui-control/SKILL.md`](./.agents/skills/colab-comfyui-control/SKILL.md) 的 `pipeline-baseline` 区块。
   - 手动同步命令：`python .agents/hooks/sync_colab_comfyui_skill.py`；只读一致性校验：`python .agents/hooks/sync_colab_comfyui_skill.py --check`。
   - 修改操控流程规程或 Hook 脚本本身时，必须同步更新 `SKILL.md` 对应章节，并运行单元测试 `python -B -m unittest discover -s .agents/hooks/tests` 确保全部通过。
