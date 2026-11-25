# AI-Video（全云端按项目隔离：Colab A100 80GB + 5TB Google Drive · MiniMax H3 33.1B）

**100% 纯云端架构**：代码与轻量化剧本配置托管在 GitHub，所有 33.1B 模型权重、参考素材、工作流与成品视频全部存储在 **5TB Google Drive (`/MyDrive/AI_Video/`)**，**每个剧本独立一个项目文件夹**，所有所属资源严格归拢在各自项目目录下。

## 一键在 Colab 打开

| Notebook | 用途 | 推荐运行时 | 一键打开 |
| :--- | :--- | :--- | :--- |
| `00_sync_models_to_drive.ipynb` | 云对云拉取 MiniMax H3 33.1B 共享模型 + 初始化云端项目文件夹 | **免费 CPU（0 CU）** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/00_sync_models_to_drive.ipynb) |
| `01_h100_comfyui_webui.ipynb` | 调用 **A100 80GB** 挂载指定 `PROJECT_ID` 启动 ComfyUI WebUI 调试 | **A100 80GB** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/01_h100_comfyui_webui.ipynb) |
| `02_h100_batch_runner.ipynb` | 调用 **A100 80GB** 按 `PROJECT_ID` 无头批量出片 + 断点续传 + 自动关机 | **A100 80GB** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/02_h100_batch_runner.ipynb) |

---

## 5TB Google Drive 云端目录结构（全局共享层 + 独立项目层）

```text
/MyDrive/AI_Video/
├── shared/                              # 全局共享层（跨所有项目复用）
│   ├── models/                          # MiniMax H3 33.1B BF16 / Qwen3-VL / 双VAE / LoRA
│   ├── workflows/                       # 通用 ComfyUI 工作流模板
│   └── logs/                            # 系统版本锁定备份等
└── projects/                            # 每个剧本/测试短片独立一个项目文件夹！
    └── 01_rainy_signal/                 # 测试项目 01：《雨夜信号 / Rainy Signal》
        ├── project.json                 # 项目元信息
        ├── script.md                    # 剧本与分镜说明
        ├── tasks.csv                    # 本项目分镜批处理任务表
        ├── inputs/                      # 本项目专属素材（参考图 ref_linwan.png / 音视频）
        ├── workflows/                   # 本项目专属工作流 JSON（优先于 shared/workflows）
        ├── outputs/                     # 本项目生成的分镜视频 + manifest.jsonl
        └── logs/                        # 本项目运行日志
```

### 新建下一个剧本/短片项目
```bash
python scripts/new_project.py 02_cyber_chase "赛博追逐"
```
推送到 GitHub 后，在 Colab 里把 `PROJECT_ID` 改成 `02_cyber_chase`，所有输入输出会自动隔离切到 `/MyDrive/AI_Video/projects/02_cyber_chase/`。
