# AI-Video（全云端按剧本项目隔离：Colab A100 80GB + 5TB Google Drive · MiniMax H3 33.1B）

**100% 纯云端架构 + 一剧本一项目独立闭环 + 剧组四工种 AI Skills 制片体系**：代码、项目级剧组 Skills（编剧 / 美术指导 / 导演 / 剪辑 / Colab 控制）与轻量化剧本配置托管在 GitHub，所有 33.1B 模型权重、人物三层资产（骨相/换装/声纹）、场次空间光影锚点、项目专属 ComfyUI 流程与四层产出视频全部按剧本项目隔离存储在 **5TB Google Drive (`/MyDrive/AI_Video/projects/<PROJECT_ID>/`)**。

## 一键在 Colab 打开

| Notebook | 用途 | 推荐运行时 | 一键打开 |
| :--- | :--- | :--- | :--- |
| `00_sync_models_to_drive.ipynb` | 云对云拉取 MiniMax H3 33.1B 共享模型 + 初始化云端剧本项目文件夹 | **免费 CPU（0 CU）** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/00_sync_models_to_drive.ipynb) |
| `01_h100_comfyui_webui.ipynb` | 调用 **A100 80GB** 挂载指定 `PROJECT_ID` 启动 ComfyUI WebUI 调试 | **A100 80GB** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/01_h100_comfyui_webui.ipynb) |
| `02_h100_batch_runner.ipynb` | 调用 **A100 80GB** 按 `PROJECT_ID` 无头批量出片 + 断点续传 + 自动关机 | **A100 80GB** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/02_h100_batch_runner.ipynb) |

---

## 剧本项目细粒度目录结构（全局共享层 + 独立剧本项目层）

```text
/MyDrive/AI_Video/
├── shared/                                         # 全局共享层（跨所有剧本项目复用）
│   ├── models/                                     # MiniMax H3 33.1B BF16 / Qwen3-VL / 双VAE / LoRA
│   ├── workflows/                                  # 通用 ComfyUI 工作流母版模板
│   └── logs/                                       # 系统版本锁定备份等
└── projects/                                       # 以剧本项目为维度拆分，每个剧本独立闭环！
    └── 01_rainy_signal/                            # 剧本项目 01：《雨夜信号 / Rainy Signal》
        ├── project.json                            # 剧本项目元配置（画幅、帧率、角色清单、场次清单、H3 15s上限）
        ├── source_script.md                        # L0 原始剧本（短篇小说、故事、文章、文学原稿）
        ├── storyboard.md                           # L1~L4 四级漏斗分镜头剧本（基于 H3 <=15s 限制拆分）
        ├── tasks.csv                               # 本项目分镜批处理任务表（直驱 ComfyUI）
        ├── characters/                             # 人物三层资产库（每个人物拥有独立文件夹）
        │   └── linwan/                             # 角色「林晚」独立文件夹（直连 ComfyUI/input/characters/linwan/）
        │       ├── character.json                  # 骨相词 + 换装字典 (outfits) + 声纹配置
        │       ├── ref_linwan.png                  # 主形象锚定图（供 Ref2VA <Picture 1> 绑定）
        │       ├── outfits/                        # 按剧情场次拆分的服装造型锚定图（解决跨场次换装）
        │       └── voice/                          # 角色 3~8s 纯净人声干音（供 <Audio 1> 声纹锁定）
        ├── images/                                 # 视觉环境与镜头图片库（直连 ComfyUI/input/images/）
        │   ├── scenes/                             # 场次空间锚点（一场戏一文件夹，防同场景正反打穿帮）
        │   │   ├── scene01_rainy_street/scene.json # 场次 1 空间与光影设定卡 + env_master.png (<Picture 2>)
        │   │   └── scene02_midnight_cafe/scene.json# 场次 2 空间与光影设定卡 + env_master.png (<Picture 2>)
        │   ├── props/                              # 跨镜头关键剧情道具参考图
        │   └── keyframes/                          # 分镜首尾帧与突破 15s 限制的跨镜接力尾帧
        ├── audio/                                  # 全局声景与主题配乐动机参考库
        ├── workflows/                              # 本剧本项目专属的 8 套 ComfyUI 流程 JSON
        │   ├── minimax_h3_fl2va_api.json           # 文生音视频 / 首镜立锚
        │   ├── minimax_h3_i2v_api.json             # 首帧图生 / 突破15s尾帧接力
        │   ├── minimax_h3_fl2v_bridge_api.json      # 首尾帧双控闭环过渡
        │   ├── minimax_h3_ref2va_api.json          # 单图人物形象锚定 (<Picture 1>)
        │   ├── minimax_h3_ref2va_multi_api.json    # 双图联合锚定 (<Picture 1> 人物 + <Picture 2> 场景/对手)
        │   └── video_minimax_h3_*.json             # WebUI 交互工作流
        ├── outputs/                                # 产出视频全生命周期四层目录
        │   ├── raw_batches/                        # ComfyUI 原始渲染批次与 manifest.jsonl
        │   ├── selected_shots/                     # 双流质检通过的每镜最优成片 (<task_id>.mp4)
        │   ├── extracted_frames/                   # 抽取的人物定妆帧与跨镜接力尾帧
        │   └── final_cut/                          # 全片无缝拼接 + 响度归一化最终成片 (<project_id>_final.mp4)
        └── logs/                                   # 本项目运行日志
```

---

## 项目级剧组四工种 AI Skills + 云端控制 Skill（`.agents/skills/`）

| 项目级 Skill 名称 | 路径 | 核心职责 |
| :--- | :--- | :--- |
| **`screenwriter`（编剧技能）** | [`.agents/skills/screenwriter/SKILL.md`](./.agents/skills/screenwriter/SKILL.md) | 采用**四级漏斗拆解法**（`L0 原著` → `L1 场次` → `L2 序列` → `L3 ≤15s 单镜节拍 & 跨镜衔接模式`）改编 `source_script.md`，按自然语速硬核算台词容量 |
| **`art-director`（美术指导与定妆技能）** | [`.agents/skills/art-director/SKILL.md`](./.agents/skills/art-director/SKILL.md) | 建立人物三层设定（`character.json` 骨相 + `outfits/` 换装 + `voice/` 声纹）与场次空间光影卡（`images/scenes/<sid>/scene.json`），调用 `extract_anchor_frame.py` 执行首镜定妆立锚 |
| **`director`（导演技能）** | [`.agents/skills/director/SKILL.md`](./.agents/skills/director/SKILL.md) | 按 **24fps `17k+5` 时间网格（≤15s）** 设计景别、焦段、单一运镜、`L4 镜头内微时间轴 ([0s-3s])` 与 32kHz 立体声 `Audio:` 声景，路由 5 套工作流与 `<Picture 1>/<Picture 2>`，产出 `storyboard.md` 与 `tasks.csv` |
| **`film-editor`（剪辑与后期合成技能）** | [`.agents/skills/film-editor/SKILL.md`](./.agents/skills/film-editor/SKILL.md) | 执行 `ffprobe` 双流质检（`h264` + `32000Hz aac`）、通过 `--last-frame` 尾帧抽帧接力突破 H3 15 秒上限，并调用 `assemble_film.py` 完成全片拼接与 `loudnorm` 音频响度归一化 |
| **`colab-comfyui-control`（云端控制技能）** | [`.agents/skills/colab-comfyui-control/SKILL.md`](./.agents/skills/colab-comfyui-control/SKILL.md) | 通过宿主 Chrome DevTools MCP (`?authuser=1`) 自动化操控 Google Colab 免费 CPU 模型同步与 A100 80GB 无头 ComfyUI 批量出片及自动断连防烧卡 |

---

## 全流程常用命令

```bash
# 1. 新建剧本项目（自动创建原始剧本、四级漏斗分镜模板、人物三层目录、场次空间目录、产出四层目录及 8 套专属 workflows/）
python scripts/new_project.py 02_cyber_chase "赛博追逐" --characters linwan:林晚 chenmo:陈默 --scenes scene01_alley:赛博暗巷 scene02_rooftop:霓虹天台

# 2. 校验剧本项目细粒度目录完整性与 MiniMax H3 15 秒 (17k+5) 分镜约束
python scripts/validate_storyboard.py --project 02_cyber_chase

# 3. [阶段 A] 首镜出片后抽取人物/场景定妆锚点帧（或 --last-frame 抽取跨镜接力尾帧）
python scripts/extract_anchor_frame.py --project-dir projects/01_rainy_signal --video outputs/batch_20261126/rainy_cafe_shot01.mp4 --timestamp 2.5 --character linwan --scene scene01_rainy_street

# 4. [阶段 C] 全片分镜双流质检、无缝拼接与 32kHz 立体声响度归一化合成成片
python scripts/assemble_film.py --project-dir projects/01_rainy_signal
```
