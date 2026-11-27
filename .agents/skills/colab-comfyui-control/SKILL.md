---
name: colab-comfyui-control
description: >-
  当需要通过 Chrome DevTools MCP 操控 Google Colab 运行时（免费 CPU 同步模型到 5TB Google Drive、
  A100 高 RAM 部署环境与无头 ComfyUI 批处理出片）、处理 Google Drive OAuth 授权弹窗、
  动态注入或调试 Colab 单元格代码、控制 MiniMax H3 (33.1B 未剪枝 BF16) 音视频生成、
  排查显存/系统内存 OOM 或执行防烧卡自动断连时，必须加载并遵循本技能。
---

# Colab 与 ComfyUI 全自动控制规程 (`colab-comfyui-control`)

本技能定义了在 `AI-Video` 项目中通过 **Chrome DevTools MCP** 操控 **Google Colab + 5TB Google Drive + 无头 ComfyUI (`MiniMax H3`)** 的标准作业流程（SOP）与故障自愈规范。

---

## 1. 操控通道与账号红线

1. **强制使用宿主 Chrome DevTools MCP**：
   - 必须通过 `call_mcp_tool` 调用 `ServerName: "chrome-devtools-plugin_chrome-devtools"`（核心工具：`list_pages`、`navigate_page`、`take_snapshot`、`click`、`evaluate_script`、`press_key`）。
   - **严禁使用内置隔离 `browser` 子代理操作 Colab**：内置 Webview 会被 Google OAuth 弹窗的 `Cross-Origin-Opener-Policy (COOP)` / `EnableCredentialPropagation HTTP 400` 拦截，且无法穿透读取 `colab.googleusercontent.com` 跨域单元格输出 Iframe。
2. **账号显式绑定 (`?authuser=1`)**：
   - 打开任何 Colab Notebook URL 时，必须在末尾显式附加 **`?authuser=1`**（对应拥有 Colab Pro 计算单元与 5TB Google Drive 的账号 `wangsongqi233@gmail.com`）。
   - 执行单元格前，先通过 `take_snapshot` 检查顶栏账号标识，绝不能误在 `authuser=0`（无计算单元或非 5TB 云盘账号）下启动任务。
3. **运行时分层与零浪费 CU 原则**：
   - **模型下载/云盘同步**（`00_sync_models_to_drive.ipynb`）：必须确认加速器为 **CPU（None，消耗 0 CU）**。
   - **视频渲染/批处理出片**（`01_h100_comfyui_webui.ipynb` / `02_h100_batch_runner.ipynb`）：通过 `代码执行程序 (Runtime)` -> `更改运行时类型` 选择 **`A100 GPU` + `高 RAM`**。

---

## 2. Google Drive 挂载与 OAuth 弹窗自动化

1. **首次执行 `drive.mount('/content/drive')` 与 `auth.authenticate_user()`（Drive API Turbo）**：
   - `00`/`01`/`02` Notebook 默认开启 `USE_DRIVE_API_TURBO = True`，在挂载 Drive 后会触发一次 Colab `auth.authenticate_user()` OAuth 授权，以绕过 DriveFS FUSE 瓶颈，启用 **Google Drive v3 API 零落盘流水线直传（HF → Drive）** 与 **多线程 HTTP Range 分片直下（Drive → A100 SSD）**。
   - 点击单元格「运行单元」后等待 5~8 秒，若弹出站内确认框（「允许此笔记本访问您的 Google 云端硬盘文件？」或「允许此笔记本访问您的 Google 凭据？」），依次点击确认。
2. **跨标签页接管 Google OAuth 授权**：
   - 立即调用 `list_pages` 查找 URL 含 `accounts.google.com/signin/oauth` 的新弹窗 `pageId`。
   - 对该 OAuth `pageId` 调用 `take_snapshot`：
     1. 点击目标账号 `wangsongqi233@gmail.com`；
     2. 等待 3 秒后再次 `take_snapshot`，点击 `继续` / `允许`（通常需连续确认两次，直至该 OAuth `pageId` 自动关闭并从 `list_pages` 消失）。
   - **超时自愈**：若首次点击授权耗时超过 `drive.mount` 默认等待窗口导致单元格报 `ValueError: mount failed/timed out`，由于 OAuth 凭据已在当前会话缓存，直接再次点击该单元格「运行单元」即可在 10 秒内完成挂载。

---

## 3. Colab 单元格精准控制与实时日志流注入

1. **表单单元格 (`cellView: "form"`) 代码读写**：
   - 需要修改单元格代码时，先点击单元格右上角 `显示代码`，即可暴露 Monaco 编辑器实例。
   - 通过 `evaluate_script` 读写 Monaco 模型，避免模拟键盘输入长代码出错：
     ```javascript
     () => {
       const models = window.monaco.editor.getModels();
       // 定位目标单元格的模型并直接替换完整 Python 代码
       models[targetIndex].setValue(newPythonCode);
       return true;
     }
     ```
2. **预热进度监控（阶段 2 `setup_env.py`）**：
   - **首选 Drive API Turbo 模式（默认 `STAGE_BACKEND="auto"`）**：绕过 DriveFS 直接通过 Google Drive v3 API 多线程 HTTP Range 分片拉取到本地 NVMe SSD，**不产生 DriveFS 读取缓存膨胀**，预热 ~92.4GB 模型时本地盘占用仅稳定增长至 ~95 GB，且大幅缩短 A100 启动耗卡时间。
   - **DriveFS 回退模式**：若未启用或降级到 DriveFS，`copy_to_local` 从 `/content/drive` 拷入 ~92.4GB 模型时会在本地 `/` 产生临时读取缓存（峰值磁盘占用可达 `140~153 GB / 235.68 GB`，完成后回落至 `~95 GB`）。
   - **单次只允许预热 1 套 61.7GB BF16 主模型包**（如 `minimax_h3_fl2va_bf16 minimax_h3_turbo_lora`），切勿同时把 `fl2va_bf16` 与 `ref2va_bf16` 一起 `copy_to_local`，否则仍可能逼近 235GB 本地 SSD 上限。
   - 轮询期间必须使用 `schedule` 定时器（间隔 60~180 秒）配合 `take_snapshot` 观察顶栏 `RAM / 磁盘` 指标与底部状态栏，禁止高频空转轮询。
3. **无头 ComfyUI 实时日志追踪（阶段 3）**：
   - 启动 `main.py` 后台进程时加上 `python -u`，并启动后台 daemon 线程实时 tail `logs/comfyui_headless.log` 输出到单元格 stdout，以便第一时间通过 `take_snapshot` 捕获模型加载状态、8 步采样进度 (`1/8 .. 8/8`) 与任何启动报错。

---

## 4. ComfyUI + MiniMax H3 (33.1B BF16) 运行时与防 OOM 铁律

1. **严禁使用 `--normalvram` 或 `--highvram`**：
   - ComfyUI `v0.46.0+` 默认即为 `NORMAL_VRAM` 并自动启用 `comfy-aimdo DynamicVRAM` 与双流异步卸载（`Using async weight offloading with 2 streams`）。
   - `--normalvram` 已从新版 `main.py` CLI 移除（传入会报 `unrecognized arguments: --normalvram` 退出）；`--highvram` 会禁止权重卸载直接导致显存爆炸。
2. **强制启用 `--bf16-vae --cache-none`**：
   - Colab A100 常见规格为 `NVIDIA A100-SXM4-40GB`（40GB 显存 + **83.47GB 系统内存**）。
   - `qwen3vl_32b_minimax_h3_int8_convrot.safetensors` (`25.28 GB`) + `minimax_h3_fl2va_bf16.safetensors` (`61.73 GB`) 合计 **87.01 GB > 83.47 GB 系统内存**。
   - 必须传入 **`--cache-none`**：使 `Qwen3-VL` 在完成节点 `MiniMaxH3ImageToVideo` / `MiniMaxH3ReferenceToVideo` 编码后立即从系统内存彻底释放，再加载 61.73GB 的 `MiniMaxH3` 主模型与 259 项 Turbo LoRA 补丁（实测峰值系统内存稳定在 `75.9 ~ 81.3 GB / 83.47 GB`，8 步采样单步耗时约 `16.8s`）。
3. **原生节点与音视频流强约束**：
   - **分辨率**：宽、高必须为 **32 的整数倍**（标准 768p 横屏为 `1344×768`）。
   - **帧数网格**：必须满足 24fps 下 **`17k + 5` 时间网格**（`124` 帧 = 5.17 秒，`243` 帧 = 10.1 秒）。
   - **音视频同源解码**：`SamplerCustomAdvanced` 的索引 `0` (`output`) 同时连入 `VAEDecode`（配合 `minimax_h3_video_vae_fp16.safetensors`）与 `VAEDecodeAudio`（配合 `minimax_h3_audio_vae_fp32.safetensors`），经 `CreateVideo` + `SaveVideo` 输出含 `32000 Hz` 双声道 AAC 音轨的 `.mp4`。

---

## 5. 成品验收、内嵌预览与防烧卡断连

1. **FFprobe 强制双流校验**：
   - 出片后必须用 `ffprobe` 验证 `.mp4` 同时具备 `codec_type="video"` (`h264`, `1344x768`, `24/1`, `nb_frames=124`) 与 `codec_type="audio"` (`aac`, `sample_rate=32000`, `channels=2`)。
2. **Base64 离线视频播放器内嵌**：
   - 在释放 A100 前，通过 `IPython.display.HTML` 将 `.mp4` 编码为 `data:video/mp4;base64,...` 的 `<video controls autoplay loop>` 渲染到单元格输出区，确保运行时断开后用户仍可在当前 Chrome 页面直接播放预览。
3. **落盘刷写与自动释放 A100**：
   - 调试阶段可将 `AUTO_DISCONNECT` 临时设为 `False`；一旦成品验收通过，必须执行 `subprocess.run(['sync'])` 刷写 Google Drive，并立即调用 `from google.colab import runtime; runtime.unassign()` 释放 A100 计算单元。

---

## 6. 当前工程流程与配置基线（由项目级 Hook 自动同步）

> [!IMPORTANT]
> 以下区块由 `.agents/hooks/sync_colab_comfyui_skill.py` 根据仓库内 `configs/`、`scripts/`、`notebooks/` 与 `workflows/shared/` 实时生成并校验。修改任何流程脚本、配置、Notebook 或工作流模板时，项目级 Hook 会自动同步更新本区块。

<!-- pipeline-baseline:begin -->
<!-- pipeline-baseline:state 58bcc15e7e5498db572c72ad36014ae0f23d0a598bb1920cdd219a4d127b186e -->

### 6.1 运行时配置与 GPU 档位 (`configs/runtime_profile.json`)

- **云盘根目录**：`/content/drive/MyDrive/AI_Video` | **共享目录**：`shared` | **默认项目**：`01_rainy_signal` | **ComfyUI 目录**：`/content/ComfyUI`
- **默认模型包**：`minimax_h3_fl2va_bf16`, `minimax_h3_turbo_lora` （加载模式：`copy_to_local`，并发线程：`4`）

| GPU 档位 | ComfyUI 启动参数 (`comfyui_args`) | 推荐模型包 |
| :--- | :--- | :--- |
| `A100_80GB` | `--bf16-vae --cache-none --listen 127.0.0.1 --port 8188` | `minimax_h3_fl2va_bf16`, `minimax_h3_ref2va_bf16`, `minimax_h3_turbo_lora`, `minimax_h3_fl2va_int8_full` |
| `H100` | `--bf16-vae --cache-none --listen 127.0.0.1 --port 8188` | `minimax_h3_fl2va_bf16`, `minimax_h3_ref2va_bf16`, `minimax_h3_turbo_lora` |
| `A100_40GB` | `--bf16-vae --cache-none --listen 127.0.0.1 --port 8188` | `minimax_h3_fl2va_int8_full`, `minimax_h3_turbo_lora` |
| `L4` | `--cache-none --listen 127.0.0.1 --port 8188` | `minimax_h3_fl2va_int8_full` |
| `DEFAULT` | `--cache-none --listen 127.0.0.1 --port 8188` | `minimax_h3_fl2va_int8_full` |

### 6.2 云端模型包清单 (`configs/models_manifest.json`)

| 模型包 ID | 默认同步 | 包含权重文件（目标子目录/文件名） |
| :--- | :--- | :--- |
| `minimax_h3_fl2va_bf16` | 是 | `diffusion_models/minimax_h3_fl2va_bf16.safetensors` (? GB)<br/>`text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors` (? GB)<br/>`vae/minimax_h3_video_vae_fp16.safetensors` (? GB)<br/>`vae/minimax_h3_audio_vae_fp32.safetensors` (? GB) |
| `minimax_h3_ref2va_bf16` | 否 | `diffusion_models/minimax_h3_ref2va_bf16.safetensors` (? GB)<br/>`text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors` (? GB)<br/>`vae/minimax_h3_video_vae_fp16.safetensors` (? GB)<br/>`vae/minimax_h3_audio_vae_fp32.safetensors` (? GB) |
| `minimax_h3_turbo_lora` | 是 | `loras/minimax_h3_fl2v_turbo_8step_v1.2_768p_comfyui_bf16.safetensors` (? GB)<br/>`loras/minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors` (? GB) |
| `minimax_h3_fl2va_int8_full` | 否 | `diffusion_models/minimax_h3_fl2va_int8_convrot.safetensors` (? GB)<br/>`text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors` (? GB)<br/>`vae/minimax_h3_video_vae_fp16.safetensors` (? GB)<br/>`vae/minimax_h3_audio_vae_fp32.safetensors` (? GB) |
| `minimax_h3_ref2va_int8_full` | 否 | `diffusion_models/minimax_h3_ref2va_int8_convrot.safetensors` (? GB)<br/>`text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors` (? GB)<br/>`vae/minimax_h3_video_vae_fp16.safetensors` (? GB)<br/>`vae/minimax_h3_audio_vae_fp32.safetensors` (? GB) |
| `qwen3vl_bf16_optional` | 否 | `text_encoders/qwen3vl_32b_minimax_h3_bf16.safetensors` (? GB) |

### 6.3 ComfyUI 与自定义节点锁定 (`configs/nodes_lock.json`)

- **ComfyUI 核心**：`https://github.com/comfyanonymous/ComfyUI.git` @ `HEAD`
- **已启用节点**：`ComfyUI-Manager` (`HEAD`), `ComfyUI-VideoHelperSuite` (`HEAD`), `ComfyUI-KJNodes` (`HEAD`)
- **已禁用节点**：`ComfyUI-WanVideoWrapper`, `ComfyUI-LTXVideo`

### 6.4 Colab Notebooks 操控入口 (`notebooks/*.ipynb`)

| Notebook 文件 | 标题与职责 | 暴露表单参数 (`#@param`) |
| :--- | :--- | :--- |
| `notebooks/00_sync_models_to_drive.ipynb` | 00 · 纯云端高速同步 MiniMax H3 满血模型 + 初始化独立项目目录到 5TB Google Drive | `REPO_URL="https://github.com/WSQ233/AI-Video.git"`, `REPO_DIR="/content/AI-Video"`, `USE_DRIVE_API_TURBO=True`, `PROJECT_ID="01_rainy_signal"`, `MINIMAX_H3_FL2VA_BF16_FULL=True`, `MINIMAX_H3_REF2VA_BF16_FULL=False`, `MINIMAX_H3_TURBO_LORA=True`, `MINIMAX_H3_FL2VA_INT8_FULL=False`, `MINIMAX_H3_REF2VA_INT8_FULL=False`, `QWEN3VL_BF16_OPTIONAL=False`, `TRANSFER_MODE="auto"`, `FILE_WORKERS=3`, `FETCH_WORKERS=8`, `UPLOAD_CHUNK_MB=256`, `FORCE_REDOWNLOAD=False`, `HF_TOKEN_INPUT=""` |
| `notebooks/01_h100_comfyui_webui.ipynb` | 01 · Colab A100 80GB 启动 ComfyUI WebUI（按独立项目挂载云端资产） | `REPO_URL="https://github.com/WSQ233/AI-Video.git"`, `REPO_DIR="/content/AI-Video"`, `USE_DRIVE_API_TURBO=True`, `PROJECT_ID="01_rainy_signal"`, `ACTIVE_PACKS="minimax_h3_fl2va_bf16 minimax_h3_turbo_lora"`, `MODEL_LOAD_MODE="copy_to_local"`, `STAGE_BACKEND="auto"`, `RANGE_WORKERS=16`, `INSTALL_SAGEATTENTION=False`, `ENABLE_LTX_NODE=False` |
| `notebooks/02_h100_batch_runner.ipynb` | 02 · Colab A100 80GB 无头批处理量产（按独立项目隔离 + Drive API 极速预热 + 自动关机防烧卡） | `REPO_URL="https://github.com/WSQ233/AI-Video.git"`, `REPO_DIR="/content/AI-Video"`, `USE_DRIVE_API_TURBO=True`, `PROJECT_ID="01_rainy_signal"`, `ACTIVE_PACKS="minimax_h3_fl2va_bf16 minimax_h3_turbo_lora"`, `MODEL_LOAD_MODE="copy_to_local"`, `STAGE_BACKEND="auto"`, `RANGE_WORKERS=16`, `INSTALL_SAGEATTENTION=False`, `ENABLE_LTX_NODE=False`, `BATCH_NAME=""`, `AUTO_DISCONNECT=True` |
| `notebooks/03_video_face_voice_replace.ipynb` | 03 · 原片精改三段式管线（多角色定向换脸 + 本尊音色中文克隆配音 + 说话人精准口型同步） | `REPO_URL="https://github.com/WSQ233/AI-Video.git"`, `REPO_DIR="/content/AI-Video"`, `PROJECT_ID="02_yongzheng_ep12_huang"`, `WORK_DIR="/content/work_replace"`, `TTS_ENGINE="chatterbox"`, `SKIP_LIPSYNC=False`, `AUTO_DISCONNECT=True` |
| `notebooks/04_video_replace_v2_pro.ipynb` | 04 · 原片精改 v2 专业高清管线（IndexTTS-2 播音级清晰中文克隆 + 时序平滑 FFHQ-512 换脸/BiSeNet 遮罩 + ByteDance LatentSync 1.6 512px 口型） | `REPO_URL="https://github.com/WSQ233/AI-Video.git"`, `REPO_DIR="/content/AI-Video"`, `PROJECT_ID="02_yongzheng_ep12_huang"`, `WORK_DIR="/content/work_replace_v2"`, `CLIP_END_SEC=15.0`, `OUTPUT_NAME="02_yongzheng_ep12_huang_v2_15s_preview.mp4"`, `INFERENCE_STEPS=20`, `SKIP_LIPSYNC=False`, `AUTO_DISCONNECT=True` |

### 6.5 控制脚本与 CLI 参数 (`scripts/*.py`)

| 脚本路径 | 支持的 CLI 参数 |
| :--- | :--- |
| `scripts/assemble_film.py` | `--project-dir`, `--batch-name`, `--output-name`, `--normalize-audio`, `--dry-run` |
| `scripts/batch_runner.py` | `--tasks-csv`, `--workflows-dir`, `--shared-workflows-dir`, `--output-dir`, `--project-dir`, `--comfy-input-dir`, `--batch-name`, `--only-tasks`, `--override-unet`, `--tiled-vae`, `--server`, `--timeout` |
| `scripts/drive_fast_io.py` | 位置参数 / 无可选标志 |
| `scripts/extract_anchor_frame.py` | `--project-dir`, `--video`, `--timestamp`, `--last-frame`, `--character`, `--outfit`, `--scene`, `--keyframe-name`, `--out` |
| `scripts/fetch_character_refs.py` | `--project-dir`, `--characters`, `--force` |
| `scripts/freeze_locks.py` | `--comfy-dir`, `--lock-file`, `--out` |
| `scripts/new_project.py` | `--characters`, `--scenes`, `--repo-root`, `--drive-root`, `--source-video-url` |
| `scripts/prep_h3_15s_clips.py` | `--project-dir`, `--repo-root`, `--width`, `--height`, `--fps` |
| `scripts/prepare_source_video.py` | `--project-dir`, `--source-url`, `--source-video`, `--skip-download`, `--dry-run` |
| `scripts/run_h3_15s_preview.py` | `--repo-root`, `--project`, `--batch-name`, `--drive-root`, `--stage-backend`, `--range-workers`, `--force-unet` |
| `scripts/setup_env.py` | `--repo-root`, `--project`, `--packs`, `--mode`, `--stage-backend`, `--range-workers`, `--enable-ltx`, `--sageattention`, `--sync-project-configs` |
| `scripts/sync_models_to_drive.py` | `--manifest`, `--repo-root`, `--project`, `--drive-root`, `--packs`, `--hf-token`, `--transfer-mode`, `--file-workers`, `--fetch-workers`, `--upload-chunk-mb`, `--force`, `--list` |
| `scripts/validate_storyboard.py` | `--repo-root`, `--project`, `--max-seconds` |
| `scripts/video_replace_pipeline.py` | `--project-dir`, `--plan`, `--work-dir`, `--shared-models-dir`, `--stage`, `--tts-engine`, `--lipsync-repo`, `--skip-lipsync` |
| `scripts/video_replace_v2.py` | `--project-dir`, `--plan`, `--work-dir`, `--shared-models-dir`, `--stage`, `--clip-end-sec`, `--indextts-dir`, `--indextts-ckpt-dir`, `--latentsync-dir`, `--latentsync-ckpt-dir`, `--output-name`, `--inference-steps`, `--skip-lipsync` |

### 6.6 共享 ComfyUI 工作流模板 (`workflows/shared/*.json`)

| 工作流文件 | 类型与规模 | 动态替换占位符 |
| :--- | :--- | :--- |
| `workflows/shared/minimax_h3_fl2v_bridge_api.json` | API 工作流 (17 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE_2__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_fl2va_api.json` | API 工作流 (15 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_i2v_api.json` | API 工作流 (16 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_ref2va_api.json` | API 工作流 (16 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_ref2va_multi3_api.json` | API 工作流 (18 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE_2__`, `__IMAGE_3__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_ref2va_multi_api.json` | API 工作流 (17 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE_2__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_ref2va_video_api.json` | API 工作流 (17 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__VIDEO__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_ref2va_video_audio_api.json` | API 工作流 (19 节点) | `__AUDIO__`, `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE_2__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__VIDEO__`, `__WIDTH__` |
| `workflows/shared/minimax_h3_ref2va_video_multi_api.json` | API 工作流 (18 节点) | `__FPS__`, `__FRAMES__`, `__HEIGHT__`, `__IMAGE_2__`, `__IMAGE__`, `__OUTPUT_PREFIX__`, `__PROMPT__`, `__SEED__`, `__VIDEO__`, `__WIDTH__` |
| `workflows/shared/video_minimax_h3_i2v.json` | UI 工作流 (9 节点) | 无（静态 UI 模板） |
| `workflows/shared/video_minimax_h3_r2v.json` | UI 工作流 (29 节点) | 无（静态 UI 模板） |
| `workflows/shared/video_minimax_h3_t2v.json` | UI 工作流 (6 节点) | 无（静态 UI 模板） |

<!-- pipeline-baseline:end -->
