---
name: director
description: >-
  AI-Video 项目级导演技能（Director Skill）。当需要将编剧（screenwriter）拆解的四级漏斗戏剧节拍与
  美术指导（art-director）锁定的人物/场次锚定资产转化为专业的视听分镜头剧本
  （projects/<project_id>/storyboard.md）与 ComfyUI 批处理任务表（projects/<project_id>/tasks.csv），
  基于 MiniMax H3 的 15 秒单镜限制（24fps 下 17k+5 帧数网格）设计景别、焦段、单一运镜、L4 镜头内微时间轴、
  32kHz 原生立体声音轨，并路由至项目下 5 套专属 ComfyUI API 流程（fl2va / i2v / fl2v_bridge /
  ref2va / ref2va_multi）时，必须加载并遵循本技能。
---

# AI-Video 项目级导演技能规程 (`director`)

本技能定义了如何以**电影导演与 AI 视听总控**视角，接棒 [`screenwriter`（编剧技能）](../screenwriter/SKILL.md) 的四级漏斗戏剧节拍与 [`art-director`（美术指导技能）](../art-director/SKILL.md) 的人物/场景设定资产，基于 **MiniMax H3 (33.1B 未剪枝 BF16) 的 15 秒物理上限与多模态参考特性**，完成镜头调度、5 套工作流精准路由、L4 镜头内微时间轴编排，并输出可直接驱动 ComfyUI 量产的 `storyboard.md` 与 `tasks.csv`。

---

## 1. 导演全局资产与项目内 5 套 API 工作流路由矩阵

每个剧本项目 (`projects/<project_id>/workflows/`) 内置了 5 套针对不同影视拍摄需求的 API 工作流。导演必须根据分镜的**叙事功能与跨镜衔接模式 (`continuity_mode`)** 精准路由：

| 项目内工作流 (`workflows/`) | 对应拍摄场景与衔接模式 | `tasks.csv` 的 `image` 列 (`<Picture 1>` / `first_frame`) | `tasks.csv` 的 `image_2` 列 (`<Picture 2>` / `last_frame`) | Prompt 强制绑定语法 |
| :--- | :--- | :--- | :--- | :--- |
| **`minimax_h3_fl2va_api.json`** | **开场大远景建立 / 空镜 / 首镜人物立锚 (`anchor_establish`)** | 留空 `""` | 留空 `""` | 直接写视觉与 `Audio:` 描述；首镜出片后交由 `art-director` 抽帧立锚 |
| **`minimax_h3_i2v_api.json`** | **场景首帧驱动 / 突破 15s 限制的跨镜尾帧接力 (`tail_relay`)** | `images/keyframes/<prev_shot>_tail.png` 或场景首帧 | 留空 `""` | 描述从首帧画面自然延续的运镜、动作与 `Audio:` |
| **`minimax_h3_fl2v_bridge_api.json`** | **首尾帧双控闭环过渡 (`first_last_bridge`)** | `images/keyframes/<shot>_first.png` | `images/keyframes/<shot>_last.png` | 描述从首帧构图平滑过渡至尾帧构图的轨迹与 `Audio:` |
| **`minimax_h3_ref2va_api.json`** | **单人叙事 / 特写对白 / 换装锚定 (`hard_cut_ref`)** | `characters/<id>/ref_<id>.png` 或换装图 `characters/<id>/outfits/<outfit>.png` | 留空 `""` | 开头必写：`Use <Picture 1> as character reference.` |
| **`minimax_h3_ref2va_multi_api.json`** | **双人同框对手戏 /「人物+场景空间」双重锁定 (`multi_ref`)** | `characters/<id1>/ref_<id1>.png` (`<Picture 1>`) | 配角 `characters/<id2>/ref_<id2>.png` 或场景 `images/scenes/<sid>/env_master.png` (`<Picture 2>`) | 开头必写：`Use <Picture 1> as character reference and <Picture 2> as [second character / environment] reference.` |
| **`minimax_h3_ref2va_video_api.json`** | **原视频 + 单人参考图直出替换 (`video_ref_direct`)** | `characters/<id>/ref_<id>.png` (`<Picture 1>`) | `video` 列：`videos/source_clips/<shot>_src.mp4` (`<Video 1>`) | 开头必写：`Use <Video 1> as reference video..., replace the character in <Video 1> with <Picture 1> as character reference.` |
| **`minimax_h3_ref2va_video_multi_api.json`** | **原视频 + 双人参考图直出替换 (`video_multi_ref_direct`)** | `characters/<id1>/ref_<id1>.png` (`<Picture 1>`) | `characters/<id2>/ref_<id2>.png` (`<Picture 2>`) + `video` 列 (`<Video 1>`) | 开头必写：`Use <Video 1> as reference video..., replace ... with <Picture 1> ... and <Picture 2> ...` |

---

## 2. 导演铁律一：MiniMax H3 15 秒上限与 `17k + 5` 时间网格精算

1. **严禁单镜超过 15 秒**：
   - MiniMax H3 在 24fps 下单次生成硬上限为 **15 秒**。
   - 帧数 `frames` 必须严格满足 **`frames = 17k + 5`**（`(frames - 5) % 17 == 0`）。
   - 官方换算公式：`max(5, round(duration_sec * 24)) + (5 - (max(5, round(duration_sec * 24)) % 17)) % 17`。
2. **8 档标准帧数与 L4 镜头内微时间轴要求（@24fps）**：

| 档位定位 | 时长 (`≤15s`) | 精确帧数 (`frames`) | 系数 `k` | 是否需要 L4 镜头内微时间轴分段 (`[0s-Xs]`) |
| :--- | :---: | :---: | :---: | :--- |
| **极短快切档** | `2.33s` | **`56`** | `3` | 否（单一瞬态反应特写） |
| **短镜节奏档** | `3.75s` | **`90`** | `5` | 否（单一利落动作 + 短句） |
| **主力标准档（首选）** | **`5.17s`** | **`124`** | `7` | 推荐拆分为 2 个微节拍（`[0.0s-1.8s]` 动作建立 + `[1.8s-5.17s]` 核心反应/对白） |
| **中长调度档** | `6.58s` | **`158`** | `9` | 必须拆分为 2 个微节拍 |
| **长镜叙事档** | `8.00s` | **`192`** | `11` | **强制在 Prompt 内标注 2~3 段 `[0s-3s] / [3s-8s]` 微时间轴**，防前快后呆 |
| **史诗长镜档** | **`10.13s`** | **`243`** | `14` | **强制在 Prompt 内标注 3 段微时间轴** |
| **准极限长镜档** | `12.25s` | **`294`** | `17` | **强制在 Prompt 内标注 3~4 段微时间轴** |
| **H3 15秒封顶档** | **`14.38s`** | **`345`** | `20` | **严格 ≤ 15.0s 最高安全档**；超出此长度必须拆镜并用 `tail_relay` 尾帧接力！ |

---

## 3. 导演铁律二：六段式声画同源 Prompt 公式与 L4 微时间轴控制

MiniMax H3 使用 `Qwen3-VL 32B` 编码器，导演在编写 `tasks.csv` 的 `prompt` 列时，必须按以下六段式组装为连续文本：

```text
[1. 参考图绑定 (<Picture 1> / <Picture 2>)] + [2. 景别、镜头焦段与单一运镜] + [3. 人物固定视觉锚点 (face_anchor_en + 当前场次 outfit) 与 L4 微时间轴动作调度] + [4. 场次空间锚点 (spatial_anchor_en) 与物理细节] + [5. 场次光影色温方案 (lighting_palette_en)] + [6. Audio: 动作拟音 + 场次底噪 (base_ambience_en) + 角色人声对白 + 音乐铺底]
```

### 3.1 跨场次光影与人物造型一致性绑定
- 编写某场次（如 `scene02_midnight_cafe`）下的分镜时，导演必须先读取 `images/scenes/scene02_midnight_cafe/scene.json`，将该场次的 `lighting_palette_en` 与 `base_ambience_en` 注入该场所有分镜，确保同场戏不同机位的光影色温与背景底噪高度一致。
- 读取 `characters/<id>/character.json`，根据角色在当前场次所穿造型（`outfits/<outfit_id>`），注入对应的造型描述与参考图。

### 3.2 原生 32kHz 立体声 `Audio:` 四层声景与口型双重锁死
1. **口型文本双重一致**：凡含人物说话的镜头，画面动作段中的引号台词 `'...'` 与末尾 `Audio:` 段中的引号台词 `'...'` 必须 **100% 一字不差**！
2. **四层声景顺序**：`Audio: [1. 与画面动作卡点的瞬态拟音 Foley] + [2. 场次空间环境底噪 Ambience] + [3. 音乐氛围 Undertone] + [4. 角色音色描述 (voice_anchor_en) + 精确台词]`。

---

## 4. 导演标准作业流程（SOP）与三阶段量产协同

1. **审阅编剧节拍与美术设定**：确认 `source_script.md`、`characters/*/character.json` 与 `images/scenes/*/scene.json` 已就绪。
2. **输出四级漏斗分镜头剧本 `projects/<project_id>/storyboard.md`**：
   - 包含：细粒度资产目录树、人物造型与声纹设定表、L1 场次空间锚点表、L2/L3 ≤15s 分镜与衔接模式总表、L4 逐镜微时间轴导演台本。
3. **输出批处理任务表 `projects/<project_id>/tasks.csv`**：
   - 标准列：`task_id,workflow,prompt,negative_prompt,image,seed,width,height,frames,fps`（如需双图/首尾帧可追加可选列 `image_2`）。
4. **执行自动化分镜校验（强制门禁）**：
   ```powershell
   python scripts/validate_storyboard.py --project <project_id>
   ```
5. **协同三阶段渲染与后期成片**：
   - **阶段 A（定妆立锚）**：先跑首镜 `FL2VA` → 交由 [`art-director`](../art-director/SKILL.md) 运行 `scripts/extract_anchor_frame.py` 提取人物/场景锚定图；
   - **阶段 B（全片分镜量产）**：运行 `scripts/batch_runner.py` 批量渲染全片 `Ref2VA / I2V` 分镜（若有 `tail_relay` 跨镜接力，中途调用 `extract_anchor_frame.py --last-frame` 提取尾帧）；
   - **阶段 C（剪辑合成）**：交由 [`film-editor`](../film-editor/SKILL.md) 运行 `scripts/assemble_film.py` 完成双流质检与全片合成。
