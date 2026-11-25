# AI-Video（Colab A100 + 5TB Google Drive 开源视频生产线）

面向 **Google Colab A100（40GB 优先，自动兼容 A100 80GB / H100 / L4）** 与 **Google AI Pro 5TB 云盘** 打造的稳定、零 OOM、可复现开源 AI 视频工程。

## 一键在 Colab 打开

| Notebook | 用途 | 推荐运行时 | 一键打开 |
| :--- | :--- | :--- | :--- |
| `00_sync_models_to_drive.ipynb` | 按包高速拉取开源模型到 5TB Google Drive | **免费 CPU（0 CU）** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/00_sync_models_to_drive.ipynb) |
| `01_h100_comfyui_webui.ipynb` | 启动 ComfyUI WebUI（Cloudflare 隧道），交互调试并导出 API 工作流 | **A100 / H100 / L4** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/01_h100_comfyui_webui.ipynb) |
| `02_h100_batch_runner.ipynb` | 无头批处理量产（CSV 驱动 + 断点续传 + 跑完自动释放防烧卡） | **A100 / H100** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/02_h100_batch_runner.ipynb) |

---

## Colab A100 40GB 最强性能模型组合（`configs/models_manifest.json`）

> **为什么 A100 40GB 首选 `FP8 Scaled` / `INT8-ConvRot` 而不是 `FP16`？**
> Wan 2.2 14B FP16 单专家权重高达 28.6GB（+11.4GB UMT5），在 40GB 显存上极易 OOM 或触发极慢的 CPU BlockSwap；而 **`fp8_scaled`** 保留动态范围、肉眼几乎无损，且可 100% 驻留 A100 40GB HBM2e 满速推理！

| Pack ID | 说明 | 体积 | 协议 / Token | A100 40GB 定位 |
| :--- | :--- | :--- | :--- | :--- |
| **`wan22_i2v_fp8`** ⭐ | **Wan 2.2 14B 图生视频 FP8 Scaled**（High+Low+UMT5 FP8+VAE） | ~36 GB | Apache 2.0 / 免 Token | **主力画质之王**（最稳、商用无忧） |
| **`wan22_lightx2v_lora`** ⭐ | **LightX2V 4步蒸馏加速 LoRA**（Rank64 High+Low） | ~2.5 GB | Apache 2.0 / 免 Token | **必装加速器**（30步变4~8步，提速4~5倍） |
| **`flux2_keyframe`** ⭐ | **FLUX.2 [dev] FP8 Mixed**（首帧关键帧生图主力） | ~45 GB | 社区协议 / 免 Token | **先定角色与构图再喂给 Wan 2.2 I2V** |
| `wan22_t2v_fp8` | Wan 2.2 14B 纯文生视频 FP8 Scaled（复用编码器） | ~29 GB | Apache 2.0 / 免 Token | 纯文字直接出片备选 |
| `ltx25_av_a100` | **LTX-2.5 22B INT8-ConvRot 原生音画同步包** | ~39 GB | LTX 协议 / 需 `HF_TOKEN` | **有声视频最强**（对白+音效一次同步生成） |
| `wan22_i2v_fp16` | Wan 2.2 14B FP16 满血版 | ~69 GB | Apache 2.0 / 免 Token | 仅限 80GB 显存（A100 80GB / H100） |

---

## 3 步快速跑通流程

1. **零算力下模型（0 CU）**：用免费 CPU 打开 `00_sync_models_to_drive.ipynb`，直接按默认勾选下载 A100 40GB 黄金三件套到 `/MyDrive/AI_Video/models/`。
2. **A100 调试标杆工作流**：切 A100 打开 `01_h100_comfyui_webui.ipynb`，从 ComfyUI 网页端测试 **FLUX.2 生首帧 -> Wan 2.2 I2V + LightX2V 4步出片**，导出 `Save (API Format)` 到 `/MyDrive/AI_Video/workflows/wan22_i2v_api.json`。
3. **A100 无头批量量产**：编辑 `/MyDrive/AI_Video/tasks/tasks.csv`，运行 `02_h100_batch_runner.ipynb`（默认 `AUTO_DISCONNECT = True`，跑完同步自动释放算力）。
