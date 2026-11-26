# 分镜头剧本：《雨夜信号 / Rainy Signal》（四级漏斗拆解版）

- **项目 ID**：`01_rainy_signal`
- **原始剧本来源**：[`source_script.md`](./source_script.md)
- **协同技能矩阵**：`screenwriter`（编剧技能） → `art-director`（美术与定妆立锚技能） → `director`（导演技能） → `film-editor`（剪辑与成片合成技能）
- **生成引擎与硬约束**：MiniMax H3 33.1B 未剪枝 BF16（`FL2VA` + `Ref2VA` + `Turbo LoRA`），**单镜头严格 ≤ 15 秒**（遵循 24fps 下 `17k + 5` 帧数时间网格）
- **画幅与音轨规格**：`1344×768`（标准 768p 16:9，32 的整数倍），`24 fps`，原生 **32kHz 双声道立体声音画同源**

---

## 一、剧本项目细粒度资产树

```text
projects/01_rainy_signal/
├── project.json                                  # 剧本项目元配置
├── source_script.md                              # L0 原始剧本（短篇小说原稿）
├── storyboard.md                                 # L1~L4 四级漏斗分镜头剧本
├── tasks.csv                                     # 分镜批处理任务表（直驱 ComfyUI）
├── characters/                                   # 人物图片与声纹资源（一人一独立文件夹）
│   └── linwan/                                   # 角色「林晚」独立目录
│       ├── character.json                        # 核心骨相锚点 + 换装字典 + 声纹配置
│       ├── ref_linwan.png                        # 主形象锚定图 (<Picture 1>)
│       ├── outfits/                              # 按场次/状态拆分的服装造型锚定图
│       └── voice/                                # 角色 3~8s 纯净人声干音 (<Audio 1>)
├── images/                                       # 视觉环境与关键帧图片资源
│   ├── scenes/                                   # 场次空间锚点（一场戏一独立文件夹，防正反打穿帮）
│   │   ├── scene01_rainy_street/scene.json       # 场次 1：赛博雨夜长街空间与光影设定卡
│   │   └── scene02_midnight_cafe/scene.json      # 场次 2：午夜咖啡馆室内空间与光影设定卡
│   ├── props/                                    # 关键剧情道具锚定图
│   └── keyframes/                                # 分镜首尾帧与跨镜尾帧接力图
├── audio/                                        # 主题配乐动机与标志性音效库
├── workflows/                                    # 本剧本项目专属的 8 套 ComfyUI 流程 JSON
│   ├── minimax_h3_fl2va_api.json                 # 文生音视频 / 首镜立锚
│   ├── minimax_h3_i2v_api.json                   # 首帧图生 / 突破15s尾帧接力
│   ├── minimax_h3_fl2v_bridge_api.json           # 首尾帧双控闭环过渡
│   ├── minimax_h3_ref2va_api.json                # 单图人物形象锚定 (<Picture 1>)
│   ├── minimax_h3_ref2va_multi_api.json          # 多图锚定 (<Picture 1> 人物 + <Picture 2> 场景/对手)
│   └── video_minimax_h3_*.json                   # WebUI 交互工作流
└── outputs/                                      # 产出视频全生命周期四层目录
    ├── raw_batches/                              # ComfyUI 原始渲染批次与 manifest.jsonl
    ├── selected_shots/                           # 验收通过的每镜最优成片
    ├── extracted_frames/                         # 抽取的人物定妆帧与跨镜接力尾帧
    └── final_cut/                                # 音画拼接与响度归一化后的完整短片成片
```

---

## 二、L1 场次空间锚点与人物造型映射表

| 场次 ID (`scene_id`) | 场次标题 | 空间与光影设定卡 | 环境主色调与色温对比 | 基础环境底噪 (`base_ambience_en`) | 林晚当前造型 (`outfit_id`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `scene01_rainy_street` | `EXT. 旧城区赛博雨夜长街 - 子夜` | [`scene.json`](./images/scenes/scene01_rainy_street/scene.json) | 冷蓝青色积水霓虹反光 vs 远处咖啡馆琥珀暖光 | 密集雨打透明伞面声、远处低沉车流、踩水声 | `outfit_01_rain_trenchcoat`（卡其色长风衣+透明雨伞） |
| `scene02_midnight_cafe` | `INT. MIDNIGHT CAFE 咖啡馆内 - 子夜` | [`scene.json`](./images/scenes/scene02_midnight_cafe/scene.json) | 室内钨丝灯暖琥珀色 vs 玻璃雨窗外冷蓝霓虹及手机蓝光 | 室外雨声衰减、室内黑胶爵士乐、玻璃雨滴轻叩 | `outfit_01_rain_trenchcoat`（收起湿雨伞，捧白瓷杯） |

---

## 三、L2/L3 基于 MiniMax H3 15 秒限制的分镜节拍与跨镜衔接总表

> [!IMPORTANT]
> - **H3 15 秒硬红线**：所有分镜严格满足 `duration = frames / 24 <= 15.0s` 且 `frames = 17k + 5`。
> - **跨镜衔接模式 (`continuity_mode`)**：
>   - `anchor_establish`：首镜建立并调用 `scripts/extract_anchor_frame.py` 提取角色/场景基准帧；
>   - `hard_cut_ref`：机位/景别切换，通过 `Ref2VA` 绑定 `characters/linwan/ref_linwan.png` (`<Picture 1>`) 锁定人物；
>   - `tail_relay`（可选扩展）：当单场连续运镜超过 15 秒时，自动提取上一镜最末帧作为下一镜 `first_frame` 无缝接力。

| 镜号 (`task_id`) | 所属场次 (`scene_id`) | 戏剧序列与节拍 (L2/L3 Beat) | 衔接模式 | 景别与单一运镜 | 项目专属工作流 (`workflows/`) | 绑定资源 (`image`) | 帧数 (`17k+5`) | 时长 (`≤15s`) |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- | :---: | :---: |
| `rainy_cafe_shot01` | `scene01_rainy_street` | **起（寻觅）**：雨夜街头持伞独行，走向亮着 `"MIDNIGHT CAFE"` 的暖光店门 | `anchor_establish` | 全景 · 35mm 缓慢前推 (`steady slow dolly-in`) | `minimax_h3_fl2va_api.json` | 首镜产出后提取 `characters/linwan/ref_linwan.png` | `124` (`k=7`) | **5.17s** |
| `rainy_cafe_shot02` | `scene02_midnight_cafe` | **承（伪装）**：推门触发黄铜风铃、收伞走到蒸汽吧台、微笑自然点单 | `hard_cut_ref` | 中近景 (`MCU`) · 吧台平稳跟拍 | `minimax_h3_ref2va_api.json` | `characters/linwan/ref_linwan.png` (`<Picture 1>`) | `124` (`k=7`) | **5.17s** |
| `rainy_cafe_shot03` | `scene02_midnight_cafe` | **转/合（觉醒）**：隔雨窗特写捧杯轻抿，手机蓝光骤亮映脸，低语信号回归 | `hard_cut_ref` | 特写 (`CU`) · 隔窗缓拉 (`gentle pull-back`) | `minimax_h3_ref2va_api.json` | `characters/linwan/ref_linwan.png` (`<Picture 1>`) | `124` (`k=7`) | **5.17s** |

---

## 四、L4 逐镜导演台本与镜头内微时间轴（Intra-Shot Micro-Timeline）

### 分镜 1（`rainy_cafe_shot01`）· 街头全景推镜与首镜人物立锚
- **时间网格与规格**：`124 帧` / `24 fps` = **`5.17 秒`**（`k=7`，≤ 15 秒） | 分辨率：`1344×768` | Seed：`1001`
- **场次与工作流**：`scene01_rainy_street` | `workflows/minimax_h3_fl2va_api.json`
- **L4 镜头内微时间轴拆解**：
  - `[0.0s - 2.0s]`：35mm 镜头在子夜暴雨长街平稳前推，林晚撑透明雨伞走过积水路面，雨滴在伞面逼真弹跳；
  - `[2.0s - 5.17s]`：前方复古咖啡馆琥珀色暖光铺满湿地面，门楣 `"MIDNIGHT CAFE"` 霓虹灯牌清晰发亮，店内隐约飘出温暖爵士乐。
- **画面 + 原生音频合成 Prompt**：
  > Cinematic 35mm film shot, steady slow dolly-in on a rainy midnight street in East Asia. A 25-year-old East Asian woman with shoulder-length wavy black hair wearing a beige trench coat walks along wet asphalt holding a clear umbrella, raindrops bouncing realistically off the umbrella and glowing puddles. Ahead stands a cozy vintage coffee shop with warm amber light spilling onto the wet pavement and a crisp glowing neon sign reading 'MIDNIGHT CAFE'. Reflections shimmer on the wet ground, subtle mist, shallow depth of field, photorealistic. Audio: steady midnight rain pattering on a clear plastic umbrella, distant muffled city traffic, footsteps splashing softly on wet pavement, faint warm jazz music leaking from inside the cafe.
- **Negative Prompt**：
  > `blurry, garbled text, distorted face, extra limbs, flicker, jitter, watermark, low quality`
- **美术立锚与导演验收**：
  1. `"MIDNIGHT CAFE"` 拼写准确无乱码；
  2. 运行 `python scripts/extract_anchor_frame.py --project 01_rainy_signal --video outputs/.../rainy_cafe_shot01.mp4 --timestamp 2.5 --character linwan` 自动提取定妆帧至 `characters/linwan/ref_linwan.png`。

---

### 分镜 2（`rainy_cafe_shot02`）· 推门进店与吧台点单对白
- **时间网格与规格**：`124 帧` / `24 fps` = **`5.17 秒`**（`k=7`，≤ 15 秒） | 分辨率：`1344×768` | Seed：`1002`
- **场次与工作流**：`scene02_midnight_cafe` | `workflows/minimax_h3_ref2va_api.json`
- **绑定人物资源**：`characters/linwan/ref_linwan.png` (`<Picture 1>`)
- **L4 镜头内微时间轴拆解**：
  - `[0.0s - 1.8s]`：林晚推开木质玻璃门，门楣黄铜风铃清脆作响，室外暴雨声迅速衰减，她熟练收起湿伞走向散发蒸汽的吧台；
  - `[1.8s - 5.17s]`：她在吧台前停步，朝镜头外咖啡师温和一笑，自然开口说出 9 词英文台词：`'A hot latte, please. It is pouring outside.'`。
- **画面 + 原生音频合成 Prompt**：
  > Use <Picture 1> as character reference. Medium close-up cinematic shot inside the warm amber-lit cafe. The same 25-year-old East Asian woman from <Picture 1> with shoulder-length wavy black hair in a beige trench coat pushes open the wooden glass door, folds her wet umbrella, walks up to the espresso counter with rising steam from a ceramic cup, smiles warmly at the barista, and speaks naturally: 'A hot latte, please. It is pouring outside.' Soft tungsten lighting, rain sliding down the window behind her, natural skin texture, 35mm film grain. Audio: crisp brass shop bell chiming as the door opens, muffled outdoor rain fading down, quiet vinyl jazz playing indoors, natural calm female voice speaking clearly: 'A hot latte, please. It is pouring outside.'
- **Negative Prompt**：
  > `blurry, lip sync mismatch, distorted face, deformed hands, flicker, watermark, low quality`
- **导演验收标准**：
  1. 推门动作与黄铜风铃声卡点精准；
  2. 林晚面部骨相、发型、卡其色风衣与 `<Picture 1>` 完全一致；
  3. 9 词台词口型同步自然。

---

### 分镜 3（`rainy_cafe_shot03`）· 窗边凝视、蓝光亮屏与悬念收尾
- **时间网格与规格**：`124 帧` / `24 fps` = **`5.17 秒`**（`k=7`，≤ 15 秒） | 分辨率：`1344×768` | Seed：`1003`
- **场次与工作流**：`scene02_midnight_cafe` | `workflows/minimax_h3_ref2va_api.json`
- **绑定人物资源**：`characters/linwan/ref_linwan.png` (`<Picture 1>`)
- **L4 镜头内微时间轴拆解**：
  - `[0.0s - 1.8s]`：隔着挂满雨滴的咖啡馆玻璃窗向内特写，林晚双手捧着冒热气的白瓷杯轻抿一口放下，瓷杯与木桌发出轻响；
  - `[1.8s - 3.5s]`：桌面手机提示音清脆响起，幽蓝色冷光自下而上映亮她的脸庞，眼神由松弛瞬间转为深邃笃定；
  - `[3.5s - 5.17s]`：她轻声低语 `'Finally... the signal is back.'`，摄影机缓慢向后拉入冷暖交织的雨夜。
- **画面 + 原生音频合成 Prompt**：
  > Use <Picture 1> as character reference. Cinematic close-up through the rain-streaked cafe window looking slightly inward at the same woman from <Picture 1> in the beige trench coat sitting by the window. She gently wraps both hands around a steaming white ceramic mug, takes a slow sip, then glances down as a glowing phone screen illuminates her face with cool blue light. Her expression shifts subtly from relaxed to intrigued as she whispers softly: 'Finally... the signal is back.' Slow gentle camera pull-back into the rainy night, warm interior contrasting with cool neon blue rain reflections on glass, anamorphic bokeh. Audio: gentle clink of ceramic mug on wooden table, soft smartphone notification chime, quiet rain tapping on glass, intimate soft female whisper: 'Finally... the signal is back.', subtle cinematic ambient swell.
- **Negative Prompt**：
  > `blurry, distorted face, deformed fingers, flicker, artifacts, watermark, low quality`
- **导演与剪辑验收标准**：
  1. 瓷杯轻触声、手机提示音与低语台词时间轴严丝合缝；
  2. 全片 3 镜渲染完毕后，运行 `python scripts/assemble_film.py --project 01_rainy_signal` 自动合成为 `outputs/final_cut/01_rainy_signal_final.mp4`。
