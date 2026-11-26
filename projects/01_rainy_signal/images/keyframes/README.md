# 分镜首尾帧与跨镜接力帧目录 (`images/keyframes/`)

存放供 `minimax_h3_i2v_api.json`（单首帧 / 尾帧接力）或 `minimax_h3_fl2v_bridge_api.json`（首尾帧双控过渡）使用的关键帧图片：
- 当需要突破 MiniMax H3 的 15 秒单镜限制制作 **20~30 秒无缝长镜头** 时，通过 `python scripts/extract_anchor_frame.py --last-frame` 将上一镜的最后一帧提取至本目录（如 `shot01_tail.png`），作为下一镜的 `first_frame` 输入。
