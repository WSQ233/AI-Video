# 通用图片资源目录 (`images/`)

本目录专用于存放剧本项目 `01_rainy_signal` 的**非人物专属图片资源**（大体积媒体存放在 5TB Google Drive `/MyDrive/AI_Video/projects/01_rainy_signal/images/`，挂载时自动直连 `ComfyUI/input/images/`）：

1. **场景概念图 / 环境空镜参考图**：如 `scene_01_midnight_cafe_exterior.png`、`scene_02_cafe_counter.png`
2. **分镜首尾帧 (`FL2VA` / `I2V`)**：供 `workflows/minimax_h3_i2v_api.json` 使用的首帧 (`first_frame`) 或尾帧 (`last_frame`)
3. **关键道具参考图**：如复古霓虹灯牌、白色陶瓷马克杯等

> [!NOTE]
> 凡用于锚定具体角色长相、发型、穿搭的**人物参考图**，请统一存放在对应角色的独立文件夹 `../characters/<character_id>/` 下（例如 `../characters/linwan/ref_linwan.png`），切勿混放在本目录。
