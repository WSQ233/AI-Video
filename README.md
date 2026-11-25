# AI-Video（全云端：Colab A100 80GB + 5TB Google Drive · MiniMax H3 满血生产线）

**100% 纯云端架构**：代码托管在 GitHub，所有 33.1B 无损模型权重、素材、工作流与成品视频全部存储在 **Google AI Pro 5TB Google Drive (`/MyDrive/AI_Video/`)**，本地硬盘零占用。

## 一键在 Colab 打开

| Notebook | 用途 | 推荐运行时 | 一键打开 |
| :--- | :--- | :--- | :--- |
| `00_sync_models_to_drive.ipynb` | 云对云拉取 MiniMax H3 33.1B 无损模型进 5TB Drive（纯网络 I/O，不浪费 GPU CU） | **免费 CPU（0 CU）** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/00_sync_models_to_drive.ipynb) |
| `01_h100_comfyui_webui.ipynb` | **调用 A100 80GB 计算单元** 启动 ComfyUI WebUI（Cloudflare 隧道），调试并导出 API 工作流 | **A100 80GB** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/01_h100_comfyui_webui.ipynb) |
| `02_h100_batch_runner.ipynb` | **调用 A100 80GB 计算单元** 无头批量出片（CSV 驱动 + 断点续传 + 跑完自动释放防烧卡） | **A100 80GB** | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/WSQ233/AI-Video/blob/main/notebooks/02_h100_batch_runner.ipynb) |

---

## Colab A100 80GB 满血高配清单（`configs/models_manifest.json`）

| Pack ID | 说明 | 体积 | 定位 |
| :--- | :--- | :--- | :--- |
| **`minimax_h3_fl2va_bf16`** ⭐ | **MiniMax H3 FL2VA 33.1B 完整未剪枝无损 BF16** (`61.7GB`) + Qwen3-VL-32B INT8-ConvRot (`27GB`) + FP16 视频 VAE + FP32 音频 VAE | ~95 GB | **画质与物理细节天花板**（首尾帧/图生/文生 + 32kHz 立体声） |
| **`minimax_h3_ref2va_bf16`** ⭐ | **MiniMax H3 Ref2VA 33.1B 完整未剪枝无损 BF16**（复用编码器与双 VAE） | ~62 GB 增量 | **多图/视频/音频全能参考天花板** |
| **`minimax_h3_turbo_lora`** ⭐ | **MiniMax H3 Turbo 极速加速 LoRA** | ~2 GB | 4~8 步极速出片，大幅省 A100 计算单元 |
| `minimax_h3_fl2va_int8_full` | 33.1B 完整未剪枝 `int8_convrot` (`~31.7GB`) | ~32 GB | 跑 15s 超长高分辨率视频需要超大显存余量时切换 |
| `minimax_h3_ref2va_int8_full` | 33.1B 完整未剪枝 `int8_convrot` (`~31.7GB`) | ~32 GB | 多参考超长视频高显存余量备选 |
| `qwen3vl_bf16_optional` | Qwen3-VL-32B 完整无损 BF16 (`~65GB`) | ~65 GB | 追求 100% 全链路 BF16 时可选 |
| `flux2_keyframe` | FLUX.2 [dev] FP8 Mixed 首帧生图（可选） | ~45 GB | 需要先独立生图定首帧时可选 |

> **A100 80GB 显存调优**：`runtime_profile.json` 为 `A100_80GB` 启用 `--normalvram --bf16-vae`——Qwen3-VL-32B 编码完成后立刻自动卸载，腾出完整 80GB HBM2e 给 **61.7GB 的 33.1B 无损 BF16** 独占推理；且每次启动只把当前要跑的单个主模型（如 `minimax_h3_fl2va_bf16`，~95GB）从 5TB Drive 拷入 Colab 本地 NVMe SSD（~235GB 空间游刃有余），其余模型通过 `extra_model_paths.yaml` 随时可从 Drive 切换。
