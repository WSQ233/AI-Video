# AI-Video（全云端：Colab A100 + 5TB Google Drive 开源视频生产线）

**100% 纯云端架构**：代码托管在 GitHub，所有模型权重、素材、工作流与成品视频全部存储在 **Google AI Pro 5TB Google Drive (`/MyDrive/AI_Video/`)**，本地电脑零存储负担。

## 一键在 Colab 打开

| Notebook | 用途 | 推荐运行时 | 一键打开 |
| :--- | :--- | :--- | :--- |
| `00_sync_models_to_drive.ipynb` | 云对云高速拉取模型到 5TB Google Drive（不走本地宽带/硬盘） | **免费 CPU（0 CU）** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/00_sync_models_to_drive.ipynb) |
| `01_h100_comfyui_webui.ipynb` | 启动 ComfyUI WebUI（Cloudflare 隧道），调试并导出 API 工作流 | **A100 / H100 / L4** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/01_h100_comfyui_webui.ipynb) |
| `02_h100_batch_runner.ipynb` | 无头批处理量产（CSV 驱动 + 断点续传 + 跑完自动释放防烧卡） | **A100 / H100** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/02_h100_batch_runner.ipynb) |

---

## Colab A100 40GB 云端双引擎模型配置（`configs/models_manifest.json`）

| Pack ID | 说明 | 体积 | 定位 |
| :--- | :--- | :--- | :--- |
| **`minimax_h3_fl2va_a100`** ⭐ | **MiniMax H3 FL2VA INT8-ConvRot** + Qwen3-VL-32B + 音视频双 VAE | ~54 GB | **第一主力**：32kHz 立体声音画同步 / 最长 15 秒 / 首尾帧与图生 |
| **`minimax_h3_ref2va_a100`** ⭐ | **MiniMax H3 Ref2VA INT8-ConvRot**（复用编码器与双 VAE） | ~21 GB 增量 | **全能参考**：多图 + 视频 + 音频锁人物/声音/风格 |
| **`minimax_h3_turbo_lora`** ⭐ | **MiniMax H3 Turbo 极速 LoRA** | ~2 GB | 4~8 步极速出片，大幅省 A100 CU |
| **`wan22_i2v_fp8`** ⭐ | **Wan 2.2 14B 图生视频 FP8 Scaled** + UMT5 FP8 + VAE | ~36 GB | **第二主力**：Apache 2.0 商用无忧 / 极速轻量批处理 |
| **`wan22_lightx2v_lora`** ⭐ | **Wan 2.2 LightX2V 4步加速 LoRA** | ~2.5 GB | 搭配 Wan 2.2 提速 4~5 倍 |
| `flux2_keyframe` | FLUX.2 [dev] FP8 Mixed 首帧生图主力 | ~45 GB | 先出高质量首帧再动态化 |
| `wan22_t2v_fp8` | Wan 2.2 14B 纯文生视频 FP8（复用编码器） | ~29 GB | 纯文字直出备选 |
| `ltx25_av_a100` | LTX-2.5 22B INT8-ConvRot（需 `HF_TOKEN`） | ~39 GB | 音画同步备选引擎 |

> **A100 40GB 显存说明**：`setup_env.py` 会自动检测 A100 40GB 并启用 `--normalvram`——ComfyUI 在用 Qwen3-VL-32B 完成文本/多模态编码后会立刻卸载编码器，再把 21GB 的 H3 INT8-ConvRot 主模型满速载入 40GB HBM2e，**零 OOM 稳跑**。

---

## 全云端 3 步上线

1. **云对云拉模型（0 CU）**：打开 `00_sync_models_to_drive.ipynb`（选免费 CPU），一键将 MiniMax H3 + Wan 2.2 同步到你的 5TB Google Drive。
2. **A100 网页调试**：切 A100 打开 `01_h100_comfyui_webui.ipynb`，从 5TB Drive 秒级预热当前所需模型包到 Colab 本地 SSD，通过 Cloudflare 隧道进 ComfyUI 出片测试并导出 `workflow_api.json` 到 Drive。
3. **A100 无人值守批量出片**：编辑 Drive 中的 `/MyDrive/AI_Video/tasks/tasks.csv`，跑 `02_h100_batch_runner.ipynb`，每条完成实时写回 5TB Drive，跑完自动断开释放算力。
