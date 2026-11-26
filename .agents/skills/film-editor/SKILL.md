---
name: film-editor
description: >-
  AI-Video 项目级剪辑与后期合成技能（Film Editor & Post-Production Skill）。当需要对剧本项目
  （projects/<project_id>/）产出的分镜视频进行双流质量验收（ffprobe 校验 h264 视频流 + 32000Hz
  双声道 aac 音频流）、通过尾帧抽帧接力（scripts/extract_anchor_frame.py --last-frame）突破
  MiniMax H3 的 15 秒单镜物理上限、归档每镜最优成片（outputs/selected_shots/），以及调用
  scripts/assemble_film.py 执行全片无缝音画拼接与 EBU R128 响度归一化产出最终成片
  （outputs/final_cut/<project_id>_final.mp4）时，必须加载并遵循本技能。
---

# AI-Video 项目级剪辑与后期合成技能规程 (`film-editor`)

本技能定义了如何以**电影剪辑师（Film Editor）与后期母带总监**视角，管理剧本项目 (`projects/<project_id>/outputs/`) 从「单镜渲染毛坯」到「跨镜尾帧无缝接力」，再到「全片音画拼接与响度归一化成片交付」的完整后期流程。

> [!IMPORTANT]
> **电影剧组四工种 Skill 协同位置**：
> 1. [`screenwriter`（编剧）](../screenwriter/SKILL.md)：`L0 原著` → `L1 场次` → `L2 序列` → `L3 ≤15s 戏剧节拍`。
> 2. [`art-director`（美术指导）](../art-director/SKILL.md)：人物三层资产 (`characters/<id>/`) + 场次空间锚点 (`images/scenes/<scene_id>/`) + 首镜定妆立锚。
> 3. [`director`（导演）](../director/SKILL.md)：镜头调度 + `17k+5` 时间网格 + `L4 微时间轴` + 5 套工作流路由 → 产出 `storyboard.md` 与 `tasks.csv`。
> 4. **`film-editor`（剪辑师，本技能）**：**突破 H3 15s 限制的尾帧接力 + 分镜双流质检 + 优选归档 (`selected_shots/`) + 全片拼接与音频响度归一化 (`final_cut/`)**。

---

## 1. 剪辑师管理的 `outputs/` 全生命周期四层目录

```text
projects/<project_id>/outputs/
├── raw_batches/                         # [L1 抽卡毛坯层] ComfyUI 各批次原始输出与 manifest.jsonl
├── selected_shots/                      # [L2 精选分镜层] 剪辑师双流质检通过的每镜唯一最优成片 (<task_id>.mp4)
├── extracted_frames/                    # [L3 抽帧接力层] 提取的定妆帧与突破 15s 限制的跨镜接力尾帧
└── final_cut/                           # [L4 成片交付层] 全片无缝拼接 + 响度归一化成片 (<project_id>_final.mp4) 与合成报告
```

---

## 2. 剪辑核心法则一：突破 MiniMax H3 15 秒上限的「尾帧接力工作流（Tail-to-Head Relay）」

MiniMax H3 单次生成物理上限为 **15 秒**（24fps 下最大安全帧数 `345` 帧 = `14.38s`）。当剧本需要一段 **15 秒 ~ 45 秒不切机位的连续一镜到底（Long Take）** 时，剪辑师与导演协同执行以下**尾帧接力标准操作**：

1. **前半镜渲染（Shot A，`≤ 14.38s`）**：
   - 先渲染前半段镜头（例如 `shot04a.mp4`，`243` 帧 = `10.13s`）。
2. **无损提取最后一帧（`--last-frame`）**：
   - 调用 `scripts/extract_anchor_frame.py` 的 `--last-frame` 模式，提取 `shot04a.mp4` 的最末一帧并自动写入本项目 `images/keyframes/shot04a_tail.png`：
     ```powershell
     python scripts/extract_anchor_frame.py `
       --project-dir projects/<project_id> `
       --video projects/<project_id>/outputs/batch_YYYYMMDD/shot04a.mp4 `
       --last-frame `
       --keyframe-name shot04a_tail
     ```
3. **后半镜首帧接力渲染（Shot B，`minimax_h3_i2v_api.json`）**：
   - 在 `tasks.csv` 中，后半段镜头 `shot04b` 使用项目下 `workflows/minimax_h3_i2v_api.json`（或首尾帧双控 `minimax_h3_fl2v_bridge_api.json`），将 `image` 设为 `images/keyframes/shot04a_tail.png`。
   - 渲染完成后，两段视频首尾画面像素级咬合，拼接后即可形成突破 15 秒限制的超长连续镜头！

---

## 3. 剪辑核心法则二：分镜音视频双流硬核质检

任何进入 `outputs/selected_shots/` 的分镜 `.mp4`，必须通过以下两项检验：

1. **FFprobe 双流技术指标检验**：
   - **视频流 (`codec_type="video"`)**：编码为 `h264`，分辨率宽高符合项目设定（如 `1344×768`，32 的倍数），帧率 `24 fps`，时长与 `frames / 24` 一致且 `≤ 15.0s`。
   - **原生音频流 (`codec_type="audio"`)**：编码为 `aac`，采样率 **`32000 Hz`**，声道数 **`2`（立体声）**。严禁出现静音无音轨文件混入成片！
2. **视听连贯性人工/多模态复核**：
   - 含文字灯牌镜头无乱码（如 `"MIDNIGHT CAFE"`）；
   - `Ref2VA` 镜头人物面部骨相、发型与服装未发生跨镜突变；
   - 口型对白、动作拟音（如推门风铃、瓷杯碰撞）与画面动作卡点同步，结尾无语音被截断（若有截断，说明编剧台词超出该帧数档位容量，需将 `frames` 按 `17k+5` 上调一档重渲）。

---

## 4. 剪辑核心法则三：全片自动化拼接与 EBU R128 响度归一化合成

由于每个 ≤15 秒分镜是由 MiniMax H3 独立推理生成的，不同分镜之间的原生音频响度（Loudness）可能存在 3~6 dB 的波动。如果直接硬拼，切镜瞬间会出现明显的背景底噪跳变。

当全部分镜渲染完成后，剪辑师必须调用 **[`scripts/assemble_film.py`](../../../scripts/assemble_film.py)** 执行标准母带合成：

```powershell
# 1. 先执行 Dry-Run 检查所有分镜是否齐备且双流 (h264 + 32kHz aac) 全部合格
python scripts/assemble_film.py --project-dir projects/<project_id> --dry-run

# 2. 执行正式合成：自动归档至 outputs/selected_shots/，按 tasks.csv 顺序无缝拼接并执行 loudnorm 响度归一化
python scripts/assemble_film.py --project-dir projects/<project_id>
```

### 合成交付物清单
1. **`outputs/selected_shots/<task_id>.mp4`**：按分镜 ID 规整归档的每镜最优单镜成片。
2. **`outputs/final_cut/<project_id>_final.mp4`**：经 `libx264 (CRF 18)` + `aac 32000Hz 立体声` + `loudnorm (I=-16 LUFS, TP=-1.5 dBTP)` 标准化处理的最终完整短片。
3. **`outputs/final_cut/assembly_report.json`**：包含全片总时长、分辨率、各分镜源文件路径与流信息的完整母带检验报告。
