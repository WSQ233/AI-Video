---
name: art-director
description: >-
  AI-Video 项目级美术指导与选角定妆技能（Art Director & Casting Skill）。当需要为剧本项目
  （projects/<project_id>/）建立或管理人物三层形象资产（骨相设定 character.json、跨场次换装造型
  characters/<id>/outfits/、声纹参考 characters/<id>/voice/）、场次空间与光影锚点
  （images/scenes/<scene_id>/scene.json，防同场景正反打穿帮）、关键剧情道具（images/props/），
  或在「阶段 A：定妆立锚渲染」后调用 scripts/extract_anchor_frame.py 提取人物/场景基准帧时，
  必须加载并遵循本技能。
---

# AI-Video 项目级美术指导与选角定妆技能规程 (`art-director`)

本技能定义了如何以**电影美术指导（Art Director）与造型定妆总监**视角，在 [`screenwriter`（编剧技能）](../screenwriter/SKILL.md) 完成剧作拆解后、[`director`（导演技能）](../director/SKILL.md) 启动全片分镜量产前，构建并锁定剧本项目 (`projects/<project_id>/`) 的**人物骨相/换装/声纹资产、场景空间光影锚点与关键剧情道具**。

> [!IMPORTANT]
> **电影剧组四工种 Skill 协同位置**：
> 1. [`screenwriter`（编剧）](../screenwriter/SKILL.md)：`L0 原著` → `L1 场次` → `L2 序列` → `L3 ≤15s 戏剧节拍`。
> 2. **`art-director`（美术指导，本技能）**：锁定人物三层设定 (`characters/<id>/`) + 场次空间光影卡 (`images/scenes/<scene_id>/`) + 道具 (`images/props/`) + 执行「阶段 A：首镜立锚抽帧」。
> 3. [`director`（导演）](../director/SKILL.md)：镜头语言调度 + `17k+5` 时间网格 + `L4 微时间轴` + 5 套工作流与 `<Picture 1>/<Picture 2>` 路由 → 产出 `storyboard.md` 与 `tasks.csv`。
> 4. [`film-editor`（剪辑师）](../film-editor/SKILL.md)：突破 15s 尾帧抽帧接力 + 双流质检 + 音画拼接与响度归一化 → 产出 `outputs/final_cut/<project_id>_final.mp4`。

---

## 1. 美术指导管理的项目细粒度资产结构

```text
projects/<project_id>/
├── characters/                                   # 1. 人物三层资产库（一人一独立文件夹）
│   └── <character_id>/                           #    如 linwan/
│       ├── character.json                        #    [核心] 骨相词 + 造型字典 (outfits) + 声纹配置
│       ├── ref_<id>.png                          #    主形象锚定图（默认供 Ref2VA <Picture 1> 绑定）
│       ├── outfits/                              #    [换装层] 按场次/天气/状态拆分的服装造型锚定图
│       │   ├── outfit_01_rain_trenchcoat.png     #    场次1&2：雨夜卡其色风衣造型
│       │   └── outfit_02_indoor_knitwear.png     #    场次3：室内卸下风衣后的针织衫造型
│       └── voice/                                #    [声纹层] 3~8秒纯净人声干音（供 <Audio 1> 锁死音色）
│           └── voice_<id>.wav
└── images/                                       # 2. 视觉环境、道具与关键帧资产库
    ├── scenes/                                   #    [空间层] 一场戏一独立文件夹，防同场景正反打背景跳变
    │   └── <scene_id>/                           #    如 scene01_rainy_street/、scene02_midnight_cafe/
    │       ├── scene.json                        #    空间建筑结构、主光源色温对比与基础环境底噪设定
    │       ├── env_master.png                    #    场景全景基准图（供 Ref2VA Multi <Picture 2> 绑定）
    │       └── env_reverse.png                   #    反打机位环境基准图
    ├── props/                                    #    [道具层] 跨镜头关键剧情道具参考图
    └── keyframes/                                #    [关键帧层] 首尾帧与跨镜接力帧
```

---

## 2. 美术核心法则一：人物三层形象设定（解决「跨场次换装」与「五官骨相锁定」）

在多场次短片中，如果把角色的「五官骨相」和「某一件具体衣服」死绑在同一个不可分割的设定上，一旦剧情进入下一场戏需要脱外套或换装，模型就会穿帮。美术指导必须在 `characters/<character_id>/character.json` 中拆解出以下三层：

1. **骨相基准层 (`face_anchor_en`)**：
   - 仅描述**不随场次改变的生理特征**：年龄、族裔、性别、脸型轮廓、眼睛特征、标志性发型与发色。
   - 示例：`"25-year-old East Asian woman, shoulder-length wavy black hair, clear expressive dark eyes, delicate natural facial features"`。
2. **场次造型换装层 (`outfits` 字典 + `characters/<id>/outfits/`)**：
   - 按 `L1 场次 (Scene)` 定义角色在该场戏的服装、配饰与物理状态（如衣领上的雨滴、沾满灰尘的夹克）。
   - 每个造型对应独立的参考图路径 `characters/<id>/outfits/<outfit_id>.png`。当角色跨场次换装时，导演在 `tasks.csv` 的 `image` 列直接指向对应 `outfits/<outfit_id>.png`！
3. **声纹参考层 (`voice_anchor_en` + `characters/<id>/voice/`)**：
   - 定义角色固定的音色、语速、共鸣特征（如 `"natural calm female voice, clear English pronunciation, composed and intimate tone"`），并管理 `voice/voice_<id>.wav` 干音样本。

---

## 3. 美术核心法则二：场次空间锚点 (`images/scenes/<scene_id>/scene.json`)

同一场戏（如「午夜咖啡馆内」）往往包含推门、吧台点单、窗边入座、正反打对话等 4~8 个分镜。为防止每个分镜生成的咖啡馆墙面、灯具、窗户结构各不相同，美术指导必须为每个场次建立 `images/scenes/<scene_id>/scene.json`：

1. **`spatial_anchor_en`（固定空间结构词）**：
   - 锁定该场戏的建筑材质、标志性陈设、门窗相对位置与文字灯牌（如 `a crisp glowing neon sign reading 'MIDNIGHT CAFE'`）。
2. **`lighting_palette_en`（固定光影与双色温方案）**：
   - 锁定主光（Key Light）、轮廓光（Rim Light）与环境冷暖反差（如 `warm amber tungsten interior lighting contrasting with cool neon blue rain reflections on the window glass`），确保同一场戏所有分镜影调 100% 统一。
3. **`base_ambience_en`（场次基础声场）**：
   - 锁定该空间持续存在的背景底噪（如 `muffled outdoor rain tapping on glass, quiet vinyl lo-fi jazz playing indoors`），供该场戏所有分镜的 `Audio:` 段落复用。
4. **`env_master.png`（场景空间基准图）**：
   - 存放在 `images/scenes/<scene_id>/env_master.png`。当某分镜需要同时锁死「人物长相」与「特定室内外背景」时，配合项目下 `workflows/minimax_h3_ref2va_multi_api.json` 将人物作为 `<Picture 1>`、场景基准图作为 `<Picture 2>` 同时喂入！

---

## 4. 美术核心法则三：「阶段 A · 定妆立锚」与无损抽帧标准作业流程

当新剧本项目尚未准备现成的人物/场景参考图时，**严禁直接全量跑完所有 `Ref2VA` 分镜**（否则一旦首镜人物不理想或缺少参考图，后续分镜会全部失败或白费 A100 算力）。必须按以下两步执行「阶段 A：定妆立锚」：

1. **第一步：仅渲染首镜 / 立锚镜（`FL2VA`）**
   - 使用 `batch_runner.py --only-tasks <establishing_shot_id>` 仅运行负责建立人物或场景的首个 `minimax_h3_fl2va_api.json` 任务。
2. **第二步：调用 `scripts/extract_anchor_frame.py` 无损抽取高清锚定图**
   - 从生成的首镜 `.mp4` 中挑出人物五官最清晰、光影最标准的时间点（如 `2.5s`），一键提取并归档至人物独立文件夹与场景文件夹：
     ```powershell
     python scripts/extract_anchor_frame.py `
       --project-dir projects/01_rainy_signal `
       --video outputs/batch_20261126/rainy_cafe_shot01.mp4 `
       --timestamp 2.5 `
       --character linwan `
       --outfit outfit_01_rain_trenchcoat `
       --scene scene01_rainy_street
     ```
   - 验收 `characters/<id>/ref_<id>.png` 与 `images/scenes/<scene_id>/env_master.png` 清晰无误后，移交 [`director`（导演技能）](../director/SKILL.md) 启动全片 `Ref2VA` 分镜批量出片。
