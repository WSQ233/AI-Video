#!/usr/bin/env python3
"""
新建独立 AI 视频剧本项目的脚手架脚本（按剧本项目维度完整隔离所有细粒度资源与 ComfyUI 流程）。
用法:
  python scripts/new_project.py 02_cyber_chase "赛博追逐" --characters linwan:林晚 chenmo:陈默 --scenes scene01_alley:赛博暗巷 scene02_rooftop:霓虹天台
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def parse_id_title_specs(specs: list[str] | None, default_item: tuple[str, str]) -> list[tuple[str, str]]:
    if not specs:
        return [default_item]
    result: list[tuple[str, str]] = []
    for item in specs:
        raw = item.strip()
        if not raw:
            continue
        if ":" in raw:
            cid, cname = raw.split(":", 1)
            result.append((cid.strip(), cname.strip() or cid.strip()))
        else:
            result.append((raw, raw))
    return result or [default_item]


def main() -> int:
    parser = argparse.ArgumentParser(description="创建新的独立剧本项目目录（含原始剧本、四级漏斗分镜剧本、细粒度人物/场景/道具/关键帧目录、产出四层目录与专属 ComfyUI 流程）")
    parser.add_argument("project_id", help="剧本项目目录名，如 02_cyber_chase")
    parser.add_argument("title", help="剧本项目中文/英文标题")
    parser.add_argument(
        "--characters",
        nargs="*",
        default=None,
        help="初始人物列表，格式为 character_id:人物名（如 linwan:林晚 chenmo:陈默），每个人物生成含 outfits/ 与 voice/ 的独立文件夹",
    )
    parser.add_argument(
        "--scenes",
        nargs="*",
        default=None,
        help="初始场次列表，格式为 scene_id:场次标题（如 scene01_street:雨夜街头），每个场次在 images/scenes/ 下生成独立空间锚点文件夹",
    )
    parser.add_argument("--repo-root", default=".", help="仓库根目录")
    parser.add_argument("--drive-root", default="/content/drive/MyDrive/AI_Video", help="云盘根目录")
    parser.add_argument("--source-video-url", default="", help="可选：原视频 URL（用于原视频+参考图直出模式）")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    pdir = repo_root / "projects" / args.project_id
    characters = parse_id_title_specs(args.characters, ("protagonist", "主角"))
    scenes = parse_id_title_specs(args.scenes, ("scene01_opening", "场次1：开场空间"))

    # 1. 创建细粒度子目录体系
    subdirs = (
        "images/scenes",
        "images/props",
        "images/keyframes",
        "videos/source_clips",
        "characters",
        "audio",
        "workflows",
        "outputs/raw_batches",
        "outputs/selected_shots",
        "outputs/extracted_frames",
        "outputs/final_cut",
        "logs",
    )
    for sub in subdirs:
        (pdir / sub).mkdir(parents=True, exist_ok=True)

    (pdir / "videos" / "README.md").write_text(
        f"# 原视频与分镜参考切片目录 (`{args.project_id}/videos/`)\n\n"
        "- `raw_source.mp4`：下载存放在 5TB Google Drive 的原始长视频母片（本地 Git 不纳管大体积视频）\n"
        "- `source_clips/<task_id>_src.mp4`：按 H3 `17k+5` 时间网格（≤15s）切出的原视频参考片段，供 `minimax_h3_ref2va_video_api.json` / `minimax_h3_ref2va_video_multi_api.json` 作为 `<Video 1>` 直出替换人物\n",
        encoding="utf-8",
    )
    (pdir / "videos" / "source_clips" / ".gitkeep").write_text(
        "# 按 <=15s (17k+5) 切分的原视频分镜参考片段存放在云盘此目录\n",
        encoding="utf-8",
    )

    (pdir / "images" / "README.md").write_text(
        f"# 视觉环境与关键帧图片目录 (`{args.project_id}/images/`)\n\n"
        "- `scenes/<scene_id>/`：场次空间锚点（一场戏一独立文件夹 + `scene.json`，供 `Ref2VA <Picture 2>` 锚定同场景正反打背景一致性）\n"
        "- `props/`：跨镜头关键剧情道具参考图\n"
        "- `keyframes/`：分镜首尾帧 (`first_frame` / `last_frame`) 与突破 H3 15 秒上限的跨镜接力尾帧\n",
        encoding="utf-8",
    )
    (pdir / "images" / "props" / "README.md").write_text(
        "# 关键剧情道具图片目录 (`images/props/`)\n\n存放跨镜头反复出现的关键道具锚定图。\n",
        encoding="utf-8",
    )
    (pdir / "images" / "keyframes" / "README.md").write_text(
        "# 分镜首尾帧与跨镜尾帧接力目录 (`images/keyframes/`)\n\n"
        "存放供 `minimax_h3_i2v_api.json` 或 `minimax_h3_fl2v_bridge_api.json` 使用的首帧、尾帧及 `extract_anchor_frame.py --last-frame` 提取的跨镜接力尾帧。\n",
        encoding="utf-8",
    )
    (pdir / "audio" / "README.md").write_text(
        "# 全局声景与主题配乐参考目录 (`audio/`)\n\n存放全片主题配乐动机 (`leitmotif_bgm.wav`) 与标志性环境/动作音效。\n",
        encoding="utf-8",
    )
    (pdir / "outputs" / "README.md").write_text(
        "# 产出视频全生命周期目录 (`outputs/`)\n\n"
        "- `raw_batches/`：ComfyUI 原始渲染批次与 `manifest.jsonl`\n"
        "- `selected_shots/`：剪辑验收通过的每镜最优 `.mp4`\n"
        "- `extracted_frames/`：抽取的人物定妆帧与跨镜接力尾帧\n"
        "- `final_cut/`：`scripts/assemble_film.py` 拼接合成后的最终成片\n",
        encoding="utf-8",
    )
    for sub in ("outputs", "logs"):
        (pdir / sub / ".gitkeep").write_text(
            f"# {args.project_id}/{sub}（生成的分镜视频与日志存放在 5TB Google Drive 对应项目目录）\n",
            encoding="utf-8",
        )

    # 2. 为每个人物创建含 outfits/（换装层）与 voice/（声纹层）的独立形象目录
    character_meta_list = []
    for cid, cname in characters:
        cdir = pdir / "characters" / cid
        (cdir / "outfits").mkdir(parents=True, exist_ok=True)
        (cdir / "voice").mkdir(parents=True, exist_ok=True)
        anchor_rel = f"characters/{cid}/ref_{cid}.png"
        character_meta_list.append({
            "character_id": cid,
            "name": cname,
            "role": "核心角色",
            "folder": f"characters/{cid}",
            "anchor_image": anchor_rel,
            "outfits_dir": f"characters/{cid}/outfits",
            "voice_dir": f"characters/{cid}/voice",
        })
        char_card = {
            "character_id": cid,
            "name": cname,
            "gender": "unspecified",
            "age": 25,
            "role": "核心角色",
            "visual_anchor_en": f"a 25-year-old character ({cname}) with distinctive facial features and consistent signature outfit",
            "face_anchor_en": f"25-year-old character ({cname}), consistent facial bone structure and hairstyle",
            "wardrobe_en": "signature consistent outfit across shots",
            "voice_anchor_en": "natural clear voice matching character personality",
            "reference_images": {
                "primary": anchor_rel,
                "front_closeup": f"characters/{cid}/ref_{cid}_front.png",
                "half_body": f"characters/{cid}/ref_{cid}_half.png",
                "full_body": f"characters/{cid}/ref_{cid}_full.png",
            },
            "outfits": {
                "outfit_01_default": {
                    "label": "默认主力造型",
                    "prompt_en": "wearing signature consistent outfit",
                    "reference_image": f"characters/{cid}/outfits/outfit_01_default.png",
                }
            },
            "voice_reference": {
                "primary_wav": f"characters/{cid}/voice/voice_{cid}.wav",
                "description": "3~8 秒纯净人声参考干音（供 Ref2VA <Audio 1> 声纹锁定）",
            },
            "notes": "在 Ref2VA 分镜中通过 'Use <Picture 1> as character reference.' 绑定 primary 或对应场次 outfit 锚定图，并在 Prompt 中复现 visual_anchor_en。",
        }
        (cdir / "character.json").write_text(
            json.dumps(char_card, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (cdir / "README.md").write_text(
            f"# 人物形象独立目录：{cname} (`{cid}`)\n\n"
            f"- 主锚定图：`ref_{cid}.png`（`tasks.csv` 的 `image` 列填写 `{anchor_rel}`）\n"
            f"- 多造型换装目录：`outfits/`（按场次存放换装参考图）\n"
            f"- 声纹参考目录：`voice/`（存放 3~8s 纯净干音 `voice_{cid}.wav`）\n",
            encoding="utf-8",
        )
        (cdir / "outfits" / "README.md").write_text(
            f"# {cname} (`{cid}`) 多造型换装锚定目录\n",
            encoding="utf-8",
        )
        (cdir / "voice" / "README.md").write_text(
            f"# {cname} (`{cid}`) 声纹参考目录\n",
            encoding="utf-8",
        )

    # 3. 为每个场次创建独立空间锚点文件夹 (images/scenes/<scene_id>/scene.json)
    scene_meta_list = []
    for sid, stitle in scenes:
        sdir = pdir / "images" / "scenes" / sid
        sdir.mkdir(parents=True, exist_ok=True)
        env_rel = f"images/scenes/{sid}/env_master.png"
        scene_meta_list.append({
            "scene_id": sid,
            "title": stitle,
            "folder": f"images/scenes/{sid}",
            "anchor_image": env_rel,
        })
        scene_card = {
            "scene_id": sid,
            "title": stitle,
            "location_type": "INT/EXT",
            "time_of_day": "NIGHT",
            "spatial_anchor_en": f"cinematic environment for {stitle} with consistent spatial architecture and key props",
            "lighting_palette_en": "cinematic contrast lighting, 35mm anamorphic depth of field",
            "base_ambience_en": "realistic spatial room tone and environmental soundscape",
            "reference_images": {
                "master": env_rel,
                "reverse_angle": f"images/scenes/{sid}/env_reverse.png",
            },
        }
        (sdir / "scene.json").write_text(
            json.dumps(scene_card, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # 4. 将 ComfyUI 流程完整拷贝并存储到本剧本项目 workflows/ 目录下
    shared_wf_dir = repo_root / "workflows" / "shared"
    copied_workflows: list[str] = []
    if shared_wf_dir.exists():
        for wf_file in sorted(shared_wf_dir.glob("*.json")):
            dst_wf = pdir / "workflows" / wf_file.name
            shutil.copy2(wf_file, dst_wf)
            copied_workflows.append(wf_file.name)

    # 5. 写入剧本项目元配置 project.json
    meta = {
        "project_id": args.project_id,
        "title": args.title,
        "type": "short_film",
        "engine": "MiniMax-H3-33.1B-BF16",
        "max_shot_duration_sec": 15,
        "frame_grid_rule": "17k+5 @ 24fps (max 345 frames = 14.38s <= 15s)",
        "active_packs": [
            "minimax_h3_fl2va_bf16",
            "minimax_h3_ref2va_bf16",
            "minimax_h3_turbo_lora",
        ],
        "resolution": "1344x768",
        "fps": 24,
        "shots": 2,
        "source_video_url": args.source_video_url,
        "cloud_dir": f"{args.drive_root}/projects/{args.project_id}",
        "structure": {
            "source_script": "source_script.md",
            "storyboard": "storyboard.md",
            "tasks_csv": "tasks.csv",
            "images_dir": "images",
            "scenes_dir": "images/scenes",
            "props_dir": "images/props",
            "keyframes_dir": "images/keyframes",
            "videos_dir": "videos",
            "source_clips_dir": "videos/source_clips",
            "characters_dir": "characters",
            "audio_dir": "audio",
            "workflows_dir": "workflows",
            "outputs_dir": "outputs",
            "raw_batches_dir": "outputs/raw_batches",
            "selected_shots_dir": "outputs/selected_shots",
            "extracted_frames_dir": "outputs/extracted_frames",
            "final_cut_dir": "outputs/final_cut",
            "logs_dir": "logs",
        },
        "characters": character_meta_list,
        "scenes": scene_meta_list,
    }
    (pdir / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 6. 写入原始剧本模板 source_script.md
    first_cid, first_cname = characters[0]
    first_sid, first_stitle = scenes[0]
    (pdir / "source_script.md").write_text(
        f"# 原始剧本：{args.title} (`{args.project_id}`)\n\n"
        "- **体裁**：短篇小说 / 故事文章 / 原始文学剧本\n"
        f"- **核心人物**：{', '.join(f'{name} (`{cid}`)' for cid, name in characters)}\n"
        f"- **主要场次**：{', '.join(f'{title} (`{sid}`)' for sid, title in scenes)}\n\n"
        "---\n\n"
        "## 原文内容\n\n"
        f"（请在此粘贴或撰写《{args.title}》的原始小说、短篇故事或文章内容，随后通过 `screenwriter` → `art-director` → `director` → `film-editor` 技能矩阵，按 MiniMax H3 15 秒单镜头上限自动拆解生成 `storyboard.md` 与 `tasks.csv`。）\n",
        encoding="utf-8",
    )

    # 7. 写入分镜头剧本模板 storyboard.md
    (pdir / "storyboard.md").write_text(
        f"# 分镜头剧本：{args.title} (`{args.project_id}` · 四级漏斗拆解版)\n\n"
        f"- **项目 ID**：`{args.project_id}`\n"
        "- **原始剧本来源**：[`source_script.md`](./source_script.md)\n"
        "- **协同技能矩阵**：`screenwriter`（编剧） → `art-director`（美术定妆） → `director`（导演） → `film-editor`（剪辑合成）\n"
        "- **H3 单镜时长红线**：严格 **≤ 15 秒**（24fps 下满足 `frames = 17k + 5`，如 `56`帧=2.33s、`90`帧=3.75s、`124`帧=5.17s、`192`帧=8.00s、`243`帧=10.13s、`345`帧=14.38s）\n"
        "- **画幅与音轨规格**：`1344×768`（32 的整数倍），`24 fps`，原生 **32kHz 双声道立体声音画同源**\n\n"
        "---\n\n"
        "## 一、人物形象锚定设定表（`characters/`）\n\n"
        "| 人物 ID | 姓名 | 独立文件夹路径 | 核心锚定图 (`image`) | 换装目录 (`outfits/`) | 声纹目录 (`voice/`) |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        + "\n".join(
            f"| `{cid}` | {cname} | `characters/{cid}/` | `characters/{cid}/ref_{cid}.png` | `characters/{cid}/outfits/` | `characters/{cid}/voice/` |"
            for cid, cname in characters
        )
        + "\n\n---\n\n"
        "## 二、L1 场次空间锚点表（`images/scenes/`）\n\n"
        "| 场次 ID | 场次标题 | 空间设定卡 | 环境基准图 (`<Picture 2>`) |\n"
        "| :--- | :--- | :--- | :--- |\n"
        + "\n".join(
            f"| `{sid}` | {stitle} | `images/scenes/{sid}/scene.json` | `images/scenes/{sid}/env_master.png` |"
            for sid, stitle in scenes
        )
        + "\n\n---\n\n"
        "## 三、L2~L4 分镜列表（单镜头严格 ≤ 15 秒）\n\n"
        f"### 分镜 1（`{args.project_id}_shot01`）· 场次 `{first_sid}` 开场建立与首镜立锚（`5.17s` / `124 帧`）\n"
        "- **工作流**：`workflows/minimax_h3_fl2va_api.json`\n"
        f"- **立锚提取**：出片后运行 `python scripts/extract_anchor_frame.py --project-dir projects/{args.project_id} --video ... --character {first_cid} --scene {first_sid}`\n"
        "- **画面 + 原生音频 Prompt**：\n\n"
        f"### 分镜 2（`{args.project_id}_shot02`）· 人物锚定连续叙事与对白（`5.17s` / `124 帧`）\n"
        "- **工作流**：`workflows/minimax_h3_ref2va_api.json`\n"
        f"- **绑定人物资源**：`characters/{first_cid}/ref_{first_cid}.png` (`<Picture 1>`)\n"
        "- **画面 + 原生音频 Prompt**：`Use <Picture 1> as character reference. ... Audio: ...`\n",
        encoding="utf-8",
    )

    # 8. 写入 tasks.csv
    (pdir / "tasks.csv").write_text(
        "task_id,workflow,prompt,negative_prompt,image,seed,width,height,frames,fps\n"
        f"{args.project_id}_shot01,minimax_h3_fl2va_api.json,\"Cinematic 35mm establishing shot. Audio: natural environmental ambience.\",\"blurry, garbled text, distorted face, extra limbs, flicker, watermark, low quality\",\"\",1001,1344,768,124,24\n"
        f"{args.project_id}_shot02,minimax_h3_ref2va_api.json,\"Use <Picture 1> as character reference. Medium close-up shot of the character from <Picture 1>. Audio: clear room ambience and natural dialogue.\",\"blurry, lip sync mismatch, distorted face, deformed hands, flicker, watermark, low quality\",\"characters/{first_cid}/ref_{first_cid}.png\",1002,1344,768,124,24\n",
        encoding="utf-8",
    )

    print(f"[已创建剧本项目] {pdir}")
    print(f"  - 原始剧本     : {pdir / 'source_script.md'}")
    print(f"  - 分镜头剧本   : {pdir / 'storyboard.md'}")
    print(f"  - 批处理任务表 : {pdir / 'tasks.csv'}")
    print(f"  - 场次空间目录 : {', '.join(str(pdir / 'images/scenes' / sid) for sid, _ in scenes)}")
    print(f"  - 人物独立目录 : {', '.join(str(pdir / 'characters' / cid) for cid, _ in characters)}")
    print(f"  - 项目工作流   : {pdir / 'workflows'} (已内置 {len(copied_workflows)} 个 ComfyUI 流程)")
    print(f"  - 产出四层目录 : {pdir / 'outputs'} (raw_batches / selected_shots / extracted_frames / final_cut)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
