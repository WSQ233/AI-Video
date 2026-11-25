# 项目 01：《雨夜信号 / Rainy Signal》（30 秒 · 3 分镜测试剧本）

- **项目 ID**：`01_rainy_signal`
- **云端根目录**：`/MyDrive/AI_Video/projects/01_rainy_signal/`
- **目标引擎**：MiniMax H3 33.1B 未剪枝 BF16（`FL2VA` + `Ref2VA` + `Turbo LoRA`）
- **画幅与规格**：`1280×720`（16:9 电影感），24 fps，开启原生 **32kHz 立体声音画同步**

---

## 本项目云端资源归属
```text
/MyDrive/AI_Video/projects/01_rainy_signal/
├── project.json     # 项目元配置（模型包/画幅/帧率）
├── script.md        # 本测试剧本与分镜说明
├── tasks.csv        # 批处理分镜清单
├── inputs/          # 本项目专属参考图 (如 ref_linwan.png)、首尾帧、参考音频
├── workflows/       # 本项目微调工作流（覆盖 shared/workflows 默认模板）
├── outputs/         # 本项目生成的分镜视频、成片与 manifest.jsonl
└── logs/            # 本项目运行日志
```

---

## 人物与场景锚点
- **主角**：25 岁亚洲女性（林晚），黑色齐肩微卷发，穿卡其色长款风衣，手提透明雨伞。
- **场景**：深夜东亚赛博雨夜街头，一家温暖橘黄色灯光的小咖啡馆，门口亮着霓虹灯牌 **`"MIDNIGHT CAFE"`**。

---

## 分镜 1（00:00 – 00:10）· 街头全景推镜（`FL2VA`）
- **画面 Prompt**：
  > Cinematic 35mm film shot, steady slow dolly-in on a rainy midnight street in East Asia. A 25-year-old East Asian woman with shoulder-length wavy black hair wearing a beige trench coat walks along wet asphalt holding a clear umbrella, raindrops bouncing realistically off the umbrella and glowing puddles. Ahead stands a cozy vintage coffee shop with warm amber light spilling onto the wet pavement and a crisp glowing neon sign reading "MIDNIGHT CAFE". Reflections shimmer on the wet ground, subtle mist, shallow depth of field, moody cyberpunk-noir lighting, photorealistic, smooth cinematic motion.
- **原生音频 Prompt**：
  > Audio: steady midnight rain pattering on a clear plastic umbrella, distant muffled city traffic, footsteps splashing softly on wet pavement, faint warm jazz music leaking from inside the cafe.
- **验收**：`"MIDNIGHT CAFE"` 清晰不乱码、雨滴物理反光自然、脚步声踩点同步。跑完后截取一帧清晰女主画面保存至本项目 `inputs/ref_linwan.png`。

---

## 分镜 2（00:10 – 00:20）· 推门进店与特写对白（`Ref2VA`）
- **参考资产**：`inputs/ref_linwan.png`
- **画面 Prompt**：
  > Medium close-up cinematic shot inside the warm amber-lit cafe. The same 25-year-old East Asian woman with shoulder-length wavy black hair in a beige trench coat pushes open the wooden glass door, folds her wet umbrella, shakes off droplets, and walks up to the espresso counter. Steam rises softly from a ceramic coffee cup on the wooden bar. She looks slightly off-camera toward the barista, smiles warmly, and speaks naturally: "A hot latte, please. It's pouring outside." Soft tungsten lighting, rain sliding down the window behind her, natural skin texture, film grain.
- **原生音频 Prompt**：
  > Audio: crisp brass shop bell chiming as the door opens, muffled outdoor rain fading down, quiet vinyl lo-fi jazz playing in the warm room, natural calm female voice speaking clearly: "A hot latte, please. It's pouring outside."
- **验收**：推门风铃卡点精准、口型对白自然、人脸/风衣与分镜 1 一致。

---

## 分镜 3（00:20 – 00:30）· 窗边凝视与高潮悬念（`Ref2VA`）
- **参考资产**：`inputs/ref_linwan.png`
- **画面 Prompt**：
  > Cinematic close-up through the rain-streaked cafe window looking slightly inward at the same woman in the beige trench coat sitting by the window. She gently wraps both hands around a steaming white ceramic mug, takes a slow sip, then glances down as a glowing phone screen illuminates her face with cool blue light. Her expression shifts subtly from relaxed to intrigued as she whispers softly: "Finally... the signal is back." Slow gentle camera pull-back into the rainy night, warm interior contrasting with cool neon blue rain reflections on glass, 35mm anamorphic bokeh.
- **原生音频 Prompt**：
  > Audio: gentle clink of ceramic mug on wooden table, soft notification chime from a smartphone, quiet rain tapping steadily on glass, intimate soft female whisper: "Finally... the signal is back.", subtle cinematic ambient swell at the end.
- **验收**：陶瓷杯轻碰 + 手机提示音精准同步、冷暖光微表情细腻、无闪烁崩坏。
