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

## 4. 全云端存储与「一剧本一项目」细粒度目录规范
- **所有重型资源必须放云端（5TB Google Drive）**：模型权重、通用图片资源、人物形象锚定图、参考音视频、成品视频、运行日志一律存于 `/MyDrive/AI_Video/`，本地电脑和 Git 仓库严禁存放大体积媒体或模型文件。
- **以剧本项目为维度完整隔离**：每个剧本项目（`projects/<project_id>/`）下的所有细粒度资源与 ComfyUI 流程均存储在对应的剧本项目下。
- **全局共享层 vs 独立剧本项目层**：
  ```text
  /MyDrive/AI_Video/
  ├── shared/                                         # 跨项目复用共享层
  │   ├── models/                                     # 全部共享模型权重 (MiniMax H3 33.1B BF16 / Qwen3-VL / 双VAE / LoRA)
  │   ├── workflows/                                  # 通用 ComfyUI 工作流母版模板
  │   └── logs/                                       # 系统级日志与冻结锁备份
  └── projects/                                       # 以剧本项目为维度拆分（每个剧本独立闭环）
      └── <project_id>/                               # 如 01_rainy_signal
          ├── project.json                            # 剧本项目元配置（画幅、帧率、角色清单、场次清单、H3 15s限制）
          ├── source_script.md                        # L0 原始剧本（短篇小说、故事、文章、文学原稿）
          ├── storyboard.md                           # L1~L4 四级漏斗分镜头剧本（基于 H3 <=15s 限制拆分产出）
          ├── tasks.csv                               # 本项目可执行批处理分镜清单（与 storyboard.md 一一对应）
          ├── characters/                             # 人物三层资产库（用来锚定人物形象，每个人物拥有独立文件夹）
          │   └── <character_id>/                     # 如 linwan/（直连 ComfyUI/input/characters/<character_id>/）
          │       ├── character.json                  # 人物设定卡（骨相词 face_anchor_en + 造型字典 + 声纹配置）
          │       ├── ref_<id>.png                    # 主形象锚定图（供 Ref2VA <Picture 1> 绑定）
          │       ├── outfits/                        # [换装层] 按剧情场次拆分的服装造型锚定图
          │       └── voice/                          # [声纹层] 角色 3~8s 纯净人声干音（供 <Audio 1> 绑定）
          ├── images/                                 # 视觉环境与镜头图片资源（直连 ComfyUI/input/images/）
          │   ├── scenes/<scene_id>/                  # [场次空间锚点] 一场戏一文件夹 + scene.json + env_master.png (<Picture 2>)
          │   ├── props/                              # [关键道具层] 跨镜头核心道具参考图
          │   └── keyframes/                          # [关键帧层] 首尾帧与突破 15s 限制的跨镜接力尾帧
          ├── audio/                                  # 全局声景与主题配乐动机参考库
          ├── workflows/                              # 本剧本项目专属的 8 套 ComfyUI 流程 JSON（存储在当前剧本项目下）
          │   ├── minimax_h3_fl2va_api.json           # 文生音视频 / 首镜立锚
          │   ├── minimax_h3_i2v_api.json             # 首帧图生 / 跨镜尾帧接力
          │   ├── minimax_h3_fl2v_bridge_api.json      # 首尾帧双控闭环过渡
          │   ├── minimax_h3_ref2va_api.json          # 单图人物形象锚定 (<Picture 1>)
          │   ├── minimax_h3_ref2va_multi_api.json    # 双图联合锚定 (<Picture 1> 人物 + <Picture 2> 场景/对手)
          │   └── video_minimax_h3_*.json             # WebUI 交互工作流
          ├── outputs/                                # 产出视频全生命周期四层目录（直连 ComfyUI/output）
          │   ├── raw_batches/                        # 原始抽卡批次与 manifest.jsonl
          │   ├── selected_shots/                     # 双流质检通过的每镜最优成片 (<task_id>.mp4)
          │   ├── extracted_frames/                   # 抽取的人物定妆帧与跨镜接力尾帧
          │   └── final_cut/                          # 全片无缝拼接 + 响度归一化最终成片 (<project_id>_final.mp4)
          └── logs/                                   # 本项目运行日志
  ```
- **创建与校验新剧本项目流程**：
  ```powershell
  python scripts/new_project.py <project_id> "<项目标题>" --characters <id1>:<姓名1> --scenes <sid1>:<场次1>
  python scripts/validate_storyboard.py --project <project_id>
  ```

---

## 5. 工作流稳定性与环境锁定规范
- **极简插件原则**：MiniMax H3 直接使用 ComfyUI 原生加载，仅保留 `ComfyUI-Manager`、`ComfyUI-VideoHelperSuite`、`ComfyUI-KJNodes` 等必要节点，避免非必要第三方插件引发依赖冲突。
- **版本冻结**：在 Colab 确认首次全流程跑通后，运行 `scripts/freeze_locks.py` 导出精确 `git commit SHA` 并更新 `configs/nodes_lock.json`，确保后续每次重装 100% 可复现。
- **幂等与断点续传**：批处理脚本（`scripts/batch_runner.py`）必须基于 `task_id` 和项目目录下 `outputs/<batch>/manifest.jsonl` 实现自动跳过已完成任务与单条异常隔离，并支持 `--only-tasks` 分阶段执行。
- **模型写入原子性**：从 Hugging Face 或本地盘写入 5TB Google Drive 必须先写 `.part` 临时文件再 `os.replace()` 原子替换，防止网络中断留下损坏权重。

---

## 6. 代码安全、校验与 Git 提交流程
- **仓库信息**：`https://github.com/WSQ233/AI-Video.git`（分支 `main`，本地目录 `D:\AI\AI-Video`）。
- **严禁提交密钥**：禁止在任何代码、JSON 或 Notebook 中硬编码 `HF_TOKEN`、Google 凭证或密码；统一优先从 Colab Secrets (`google.colab.userdata`) 或环境变量读取。
- **提交前必须校验**：每次修改后、执行 `git commit` 前必须运行校验命令，确保所有 `.py` 编译通过、所有 `.json` 和 `.ipynb` 可正确解析、所有剧本项目细粒度结构与 H3 15 秒分镜约束合法：
  ```powershell
  python -c "import json, py_compile, pathlib; root=pathlib.Path(r'D:\AI\AI-Video'); [py_compile.compile(str(p), doraise=True) for p in root.rglob('*.py')]; [json.loads(p.read_text(encoding='utf-8')) for p in list(root.rglob('*.json')) + list(root.rglob('*.ipynb'))]; print('ALL VALID OK')" && python scripts/validate_storyboard.py
  ```
- **清晰的提交信息**：使用约定式提交前缀（`feat:` / `fix:` / `refactor:` / `chore:` / `docs:`），避免把 `__pycache__`、临时日志或大文件纳入版本控制。

---

## 7. 项目级剧组四工种 Skills + 云端控制 Skill 与 Hook 联动规范

1. **剧组四工种 Skills 协同规范（从原始剧本到最终成片）**：
   - **项目级编剧技能 ([`.agents/skills/screenwriter/SKILL.md`](./.agents/skills/screenwriter/SKILL.md))**：采用**四级漏斗拆解法**（`L0 原著 source_script.md` → `L1 场次 Scenes` → `L2 序列 Sequences` → `L3 ≤15s 单镜节拍 & 跨镜衔接模式`），按自然语速核算台词容量，将抽象心理描写转译为外化动作与触发声效。
   - **项目级美术指导与定妆技能 ([`.agents/skills/art-director/SKILL.md`](./.agents/skills/art-director/SKILL.md))**：负责建立人物三层设定（`characters/<id>/character.json` 骨相词 + `outfits/` 跨场次换装锚定 + `voice/` 声纹参考）、场次空间光影设定（`images/scenes/<scene_id>/scene.json`，防同场景正反打穿帮），並在「阶段 A：定妆立锚」后调用 `scripts/extract_anchor_frame.py` 无损抽取人物与场景基准图。
   - **项目级导演技能 ([`.agents/skills/director/SKILL.md`](./.agents/skills/director/SKILL.md))**：接棒编剧节拍与美术设定，按 **24fps 下 `17k + 5` 时间网格**（`56 / 90 / 124 / 158 / 192 / 243 / 294 / 345` 帧，严格 `≤ 15.0s`）与 **32 倍数分辨率**（默认 `1344×768`），设计景别、焦段、单一运镜、`L4 镜头内微时间轴 ([0s-3s])` 与 32kHz 立体声四层 `Audio:` 声景，路由至项目 `workflows/` 下 5 套专属 API 流程并绑定 `<Picture 1>` / `<Picture 2>`，产出 `storyboard.md` 与 `tasks.csv`，运行 `python scripts/validate_storyboard.py --project <project_id>` 验证通过。
   - **项目级剪辑与后期合成技能 ([`.agents/skills/film-editor/SKILL.md`](./.agents/skills/film-editor/SKILL.md))**：负责 `ffprobe` 双流质检（`h264` + `32000Hz aac`）、通过 `scripts/extract_anchor_frame.py --last-frame` 实现突破 H3 15 秒上限的**跨镜尾帧无缝接力（Tail-to-Head Relay）**、归档 `outputs/selected_shots/`，并调用 `scripts/assemble_film.py` 完成全片无缝拼接与 EBU R128 `loudnorm` 音频响度归一化（输出 `outputs/final_cut/<project_id>_final.mp4`）。
2. **操控 Colab 与 ComfyUI 必须先加载项目级云端控制 Skill**：
   - 凡涉及通过浏览器或 MCP 控制 Google Colab、处理 Google Drive 挂载授权、部署/启动 ComfyUI、执行 `MiniMax H3` 推理或排查 OOM 的任务，必须先读取并严格遵循项目级技能 [`.agents/skills/colab-comfyui-control/SKILL.md`](./.agents/skills/colab-comfyui-control/SKILL.md)。
   - **强制使用宿主 Chrome DevTools MCP (`chrome-devtools-plugin_chrome-devtools`)** 并显式附加 **`?authuser=1`**（绑定 `wangsongqi233@gmail.com`），严禁使用内置隔离 `browser` 子代理操作 Colab。
3. **流程修改与项目级 Hook 自动同步规范**：
   - 本项目已配置项目级生命周期 Hook（Antigravity [`.agents/hooks.json`](./.agents/hooks.json) 与 Codex [`.codex/hooks.json`](./.codex/hooks.json)，执行脚本为 [`.agents/hooks/sync_colab_comfyui_skill.py`](./.agents/hooks/sync_colab_comfyui_skill.py)）。
   - 每当修改 `configs/*.json`、`scripts/*.py`、`notebooks/*.ipynb` 或 `workflows/shared/*.json` 时，Hook 会自动提取最新配置、CLI 参数、Notebook 表单字段及工作流占位符，同步更新 [`.agents/skills/colab-comfyui-control/SKILL.md`](./.agents/skills/colab-comfyui-control/SKILL.md) 的 `pipeline-baseline` 区块。
   - 手动同步命令：`python .agents/hooks/sync_colab_comfyui_skill.py`；只读一致性校验：`python .agents/hooks/sync_colab_comfyui_skill.py --check`；单元测试：`python -B -m unittest discover -s .agents/hooks/tests`。
