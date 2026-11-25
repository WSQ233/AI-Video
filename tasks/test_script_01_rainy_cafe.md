# 测试短片剧本 01：《雨夜信号 / Rainy Signal》（30 秒 · 3 分镜）

- **目标引擎**：MiniMax H3 33.1B 未剪枝 BF16（`FL2VA` + `Ref2VA`）
- **画幅与规格**：`1280×720`（16:9 电影感），每镜头 `10 秒`（24 fps），开启原生 **32kHz 立体声音画同步**
- **测试覆盖点**：雨滴物理反光、霓虹招牌文字、推门风铃与环境音、人物特写口型对白、跨镜头人物与风衣一致性

---

## 人物与场景锚点（统一设定）
- **主角**：25 岁亚洲女性（林晚），黑色齐肩微卷发，穿卡其色长款风衣，手提一把透明雨伞。
- **场景**：深夜东京/上海感赛博雨夜街头，一家温暖橘黄色灯光的小咖啡馆，门口亮着霓虹灯牌 **`"MIDNIGHT CAFE"`**。

---

## 分镜 1（00:00 – 00:10）· 街头全景推镜（测试：雨夜物理 + 霓虹文字 + 环境声）
- **模式**：`FL2VA`（纯文生视频 T2AV，可直接作为整片视觉基准）
- **画面 Prompt**：
  > Cinematic 35mm film shot, steady slow dolly-in on a rainy midnight street in East Asia. A 25-year-old East Asian woman with shoulder-length wavy black hair wearing a beige trench coat walks along wet asphalt holding a clear umbrella, raindrops bouncing realistically off the umbrella and glowing puddles. Ahead stands a cozy vintage coffee shop with warm amber light spilling onto the wet pavement and a crisp glowing neon sign reading "MIDNIGHT CAFE". Reflections shimmer on the wet ground, subtle mist, shallow depth of field, moody cyberpunk-noir lighting, photorealistic, smooth cinematic motion.
- **原生音频 Prompt（与画面合并输入）**：
  > Audio: steady midnight rain pattering on a clear plastic umbrella, distant muffled city traffic, footsteps splashing softly on wet pavement, faint warm jazz music leaking from inside the cafe.
- **测试验看点**：`"MIDNIGHT CAFE"` 字母是否清晰、雨滴落伞和地面积水倒影是否自然、脚步声与画面节奏是否同步。

---

## 分镜 2（00:10 – 00:20）· 推门进店与特写对白（测试：人物一致性 + 口型对白 + 物理音效）
- **模式**：`Ref2VA`（把分镜 1 的尾帧或人物清晰帧作为参考图 `ref_linwan.png` 锁脸/锁风衣；也可先用 `FL2VA` 首帧模式直接接分镜 1 尾帧）
- **画面 Prompt**：
  > Medium close-up cinematic shot inside the warm amber-lit cafe. The same 25-year-old East Asian woman with shoulder-length wavy black hair in a beige trench coat pushes open the wooden glass door, folds her wet umbrella, shakes off droplets, and walks up to the espresso counter. Steam rises softly from a ceramic coffee cup on the wooden bar. She looks slightly off-camera toward the barista, smiles warmly, and speaks naturally: "A hot latte, please. It's pouring outside." Soft tungsten lighting, rain sliding down the window behind her, natural skin texture, film grain.
- **原生音频 Prompt**：
  > Audio: crisp brass shop bell chiming as the door opens, muffled outdoor rain fading down, quiet vinyl lo-fi jazz playing in the warm room, natural calm female voice speaking clearly: "A hot latte, please. It's pouring outside."
- **测试验看点**：风铃声是否踩在推门瞬间、人物口型与英文台词是否精准贴合、发丝与风衣是否和分镜 1 一致。

---

## 分镜 3（00:20 – 00:30）· 窗边凝视与高潮悬念（测试：微表情 + 玻璃反光 + 情绪收尾）
- **模式**：`Ref2VA`（继续引用 `ref_linwan.png`）或 `FL2VA`
- **画面 Prompt**：
  > Cinematic close-up through the rain-streaked cafe window looking slightly inward at the same woman in the beige trench coat sitting by the window. She gently wraps both hands around a steaming white ceramic mug, takes a slow sip, then glances down as a glowing phone screen illuminates her face with cool blue light. Her expression shifts subtly from relaxed to intrigued as she whispers softly: "Finally... the signal is back." Slow gentle camera pull-back into the rainy night, warm interior contrasting with cool neon blue rain reflections on glass, 35mm anamorphic bokeh.
- **原生音频 Prompt**：
  > Audio: gentle clink of ceramic mug on wooden table, soft notification chime from a smartphone, quiet rain tapping steadily on glass, intimate soft female whisper: "Finally... the signal is back.", subtle cinematic ambient swell at the end.
- **测试验看点**：陶瓷杯轻碰与手机提示音是否精准卡点、冷暖光交织下的人脸微表情自然度、整段 10 秒画面是否无闪烁崩坏。

---

## 推荐 A100 80GB 实测参数（先快测再精渲）
1. **第 1 轮快速验机（省 CU，1~2 分钟出片）**：
   - 模型：`minimax_h3_fl2va_bf16.safetensors` + **`minimax_h3_turbo_lora.safetensors`**
   - 分辨率：`1280×720`（首测可先跑 `5 秒 / 121 帧`，确认无报错后再拉满 `10 秒 / 241 帧`）
   - 步数：`6–8 steps`（Turbo LoRA）
2. **第 2 轮满血精渲（画质天花板）**：
   - 关闭 Turbo LoRA，步数：`24–30 steps`，完整 `10 秒`，导出带 32kHz 立体声 MP4 到 `/MyDrive/AI_Video/outputs/`。
