# AI-Video（Colab H100 + 5TB Google Drive 开源视频生产线）

面向 **Google Colab H100（80GB）** 与 **Google AI Pro 5TB 云盘** 打造的稳定、低算力损耗、可复现开源 AI 视频工程脚手架。

## 一键在 Colab 打开

| Notebook | 用途 | 推荐运行时 | 一键打开 |
| :--- | :--- | :--- | :--- |
| `00_sync_models_to_drive.ipynb` | 按包高速拉取开源模型到 5TB Google Drive | **免费 CPU（0 CU）** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/00_sync_models_to_drive.ipynb) |
| `01_h100_comfyui_webui.ipynb` | 启动 ComfyUI WebUI（Cloudflare 隧道），交互调试并导出 API 工作流 | **H100 / A100 / L4** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/01_h100_comfyui_webui.ipynb) |
| `02_h100_batch_runner.ipynb` | 无头批处理量产（CSV 驱动 + 断点续传 + 跑完自动释放 H100 省 CU） | **H100** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/02_h100_batch_runner.ipynb) |

---

## 核心模型包配置（`configs/models_manifest.json`）

| Pack ID | 说明 | 体积 | 协议 / Token |
| :--- | :--- | :--- | :--- |
| `wan22_i2v_fp16` ⭐ | **Wan 2.2 14B 图生视频 FP16 满血版**（High+Low+UMT5+VAE） | ~69 GB | Apache 2.0 / 免 Token |
| `wan22_lightx2v_lora` ⭐ | **LightX2V 4步蒸馏加速 LoRA**（出片提速 4~5 倍） | ~2.5 GB | Apache 2.0 / 免 Token |
| `wan22_i2v_fp8` | Wan 2.2 14B 图生视频 FP8 轻量高速版 | ~36 GB | Apache 2.0 / 免 Token |
| `wan22_t2v_fp16` | Wan 2.2 14B 文生视频 FP16 满血版 | ~57 GB | Apache 2.0 / 免 Token |
| `flux2_keyframe` | FLUX.2 [dev] FP8 Mixed 首帧关键帧生图包 | ~45 GB | 社区协议 / 免或按需 Token |
| `ltx25_av` | **LTX-2.5 22B BF16 原生音画同步视频包** | ~70 GB | LTX 协议 / 需 `HF_TOKEN` |

---

## 标准使用流程（最省 H100 CU）

1. **下模型（0 算力费）**：用免费 CPU 打开 `00_sync_models_to_drive.ipynb`，勾选 `wan22_i2v_fp16` + `wan22_lightx2v_lora`，模型自动存入 `/MyDrive/AI_Video/models/`。
2. **调工作流**：切 H100 打开 `01_h100_comfyui_webui.ipynb`，从内置模板或自定义搭建 Wan 2.2 工作流，生成验证通过后：
   - 在 ComfyUI 右上角开启 `Enable Dev mode Options` -> 点击 `Save (API Format)` 导出到 `/MyDrive/AI_Video/workflows/wan22_i2v_api.json`；
   - 可运行一次 `scripts/freeze_locks.py` 锁定稳定节点 commit SHA，提交回本仓库。
3. **批量量产（防烧卡）**：编辑 `/MyDrive/AI_Video/tasks/tasks.csv`，在 H100 上运行 `02_h100_batch_runner.ipynb`（默认 `AUTO_DISCONNECT = True`，全部生成并落盘 Drive 后自动释放运行时）。

---

## Google Drive 5TB 目录布局

```text
MyDrive/AI_Video/
├── models/       # 所有开源权重（按 ComfyUI 子目录组织）
├── inputs/       # 首帧参考图 / 角色素材（直连 ComfyUI/input）
├── workflows/    # 保存的 ComfyUI 工作流 JSON（直连 ComfyUI/user/default/workflows）
├── tasks/        # 批量生成任务 CSV
├── outputs/      # 成品视频 + manifest.jsonl（直连 ComfyUI/output，断线不丢）
└── logs/         # 启动与批处理日志
```
