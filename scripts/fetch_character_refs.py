#!/usr/bin/env python3
"""
七方人物多角度权威高清参考图自动抓取与定妆拼图工具 (art-director 专用脚本)：
- 从 Wikimedia Commons 官方 API 抓取真实公众人物的 3~4 张多角度高清官方肖像/演讲照（公有领域/CC 权威图源）
- 直接落盘至 5TB Google Drive 对应剧本项目目录 characters/<character_id>/（本地 Git 不存大体积图）
- 为每位主角保存多张独立参考图 (ref_<id>_01.png .. 04.png) 并合成无缝多角度定妆锚定图 (ref_<id>.png)，
  为民主党/共和党群像合成 2x2 多人物参考拼图，确保 MiniMax H3 Ref2VA 人物面部骨相与神态高度准确。
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


USER_AGENT = "AI-Video-ArtDirector/1.0 (https://github.com/WSQ233/AI-Video; educational research)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# 每个角色配备多张明确 Wikimedia Commons 文件名 + 搜索兜底词
CHARACTER_SOURCES: dict[str, dict[str, Any]] = {
    "trump": {
        "label": "特朗普 (Donald Trump · 替康熙)",
        "mode": "multi_angle",
        "files": [
            "File:Official Presidential Portrait of President Donald J. Trump (2025).jpg",
            "File:January 2025 Official Presidential Portrait of Donald J. Trump.jpg",
            "File:Donald Trump official portrait.jpg",
        ],
        "search_queries": ["Donald Trump 2025 speaking", "Donald Trump portrait 2025"],
        "target_count": 3,
    },
    "jensen_huang": {
        "label": "黄仁勋 (Jensen Huang · 替太子/CEO)",
        "mode": "multi_angle",
        "files": [
            "File:Jensen huang stanford 2026-04-30 008 (cropped).jpg",
            "File:Jensen Huang (cropped) (2024).jpg",
            "File:Jensen Huang Stanford 2026-04-30 010 (cropped).jpg",
            "File:Jensen Huang 20231109 (cropped2).jpg",
        ],
        "search_queries": ["Jensen Huang cropped", "Jensen Huang portrait"],
        "target_count": 3,
    },
    "scott_bessent": {
        "label": "贝森特 (Scott Bessent · 替张廷玉)",
        "mode": "multi_angle",
        "files": [
            "File:Official portrait of Treasury Secretary Scott Bessent (borderless).jpg",
            "File:Scott Bessent.jpg",
            "File:Scott Bessent, official portrait (2025).jpg",
        ],
        "search_queries": ["Scott Bessent 2025", "Scott Bessent Treasury"],
        "target_count": 3,
    },
    "marco_rubio": {
        "label": "鲁比奥 (Marco Rubio · 替佟国维)",
        "mode": "multi_angle",
        "files": [
            "File:Official portrait of Secretary Marco Rubio.jpg",
            "File:Senator Rubio official portrait.jpg",
            "File:Marco Rubio, Official Portrait, 112th Congress.jpg",
        ],
        "search_queries": ["Marco Rubio speaking cropped", "Marco Rubio portrait"],
        "target_count": 3,
    },
    "jd_vance": {
        "label": "万斯 (JD Vance · 替马齐)",
        "mode": "multi_angle",
        "files": [
            "File:January 2025 Official Vice Presidential Portrait of JD Vance.jpg",
            "File:Senator Vance official portrait. 118th Congress (cropped).jpg",
            "File:J. D. Vance (53984614485) (cropped).jpg",
            "File:J. D. Vance (53809627400) (cropped).jpg",
        ],
        "search_queries": ["JD Vance cropped", "JD Vance official portrait"],
        "target_count": 3,
    },
    "democrats": {
        "label": "民主党人士换脸群像 (舒默/佩洛西/沃伦/杰弗里斯)",
        "mode": "group_grid",
        "files": [
            "File:Chuck Schumer official photo (3x4a).jpg",
            "File:Official photo of Speaker Nancy Pelosi in 2019.jpg",
            "File:Elizabeth Warren, official portrait, 114th Congress.jpg",
            "File:Rep-Hakeem-Jeffries-Official-Portrait (cropped).jpg",
        ],
        "search_queries": ["Chuck Schumer official portrait", "Nancy Pelosi official portrait"],
        "target_count": 4,
    },
    "republicans": {
        "label": "共和党人士换脸群像 (约翰逊/卢特尼克/麦康奈尔/图恩)",
        "mode": "group_grid",
        "files": [
            "File:Speaker Mike Johnson Official Portrait (3x4 cropped).jpg",
            "File:Howard Lutnick 2025.jpg",
            "File:Mitch McConnell 2016 official photo.jpg",
            "File:John Thune 117th Congress portrait.jpg",
        ],
        "search_queries": ["Mike Johnson official portrait", "Howard Lutnick 2025"],
        "target_count": 4,
    },
}


def api_get_json(params: dict[str, Any]) -> dict[str, Any]:
    url = f"{COMMONS_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def resolve_commons_file_url(file_title: str, thumb_width: int = 1200) -> tuple[str | None, str]:
    """查询 Wikimedia Commons 文件的直链（优先取 ~1200px 高清缩略图，防超时与原图过大）。"""
    data = api_get_json({
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": thumb_width,
        "format": "json",
    })
    pages = data.get("query", {}).get("pages", {})
    for page_id, pinfo in pages.items():
        if str(page_id) == "-1" or "missing" in pinfo:
            continue
        infos = pinfo.get("imageinfo", [])
        if not infos:
            continue
        info = infos[0]
        mime = info.get("mime", "")
        if not mime.startswith("image/"):
            continue
        url = info.get("thumburl") or info.get("url")
        return url, pinfo.get("title", file_title)
    return None, file_title


def search_commons_files(query: str, limit: int = 6) -> list[str]:
    data = api_get_json({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 6,  # File: namespace
        "srlimit": limit,
        "format": "json",
    })
    results: list[str] = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        low = title.lower()
        if low.endswith((".jpg", ".jpeg", ".png", ".webp")) and "signature" not in low and "logo" not in low and "seal" not in low:
            results.append(title)
    return results


def download_image(url: str) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read()
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img).convert("RGB")
    return img


def fit_portrait_tile(img: Image.Image, tile_w: int, tile_h: int) -> Image.Image:
    """以面部偏上构图居中裁剪缩放至目标尺寸，避免切掉头顶。"""
    return ImageOps.fit(img, (tile_w, tile_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.25))


def build_composite_reference(images: list[Image.Image], mode: str) -> Image.Image:
    """将多张高清肖像拼合成无文字干扰的干净参考拼图，提升 Ref2VA 骨相与多角度一致性。"""
    if len(images) == 1:
        return fit_portrait_tile(images[0], 1024, 1024)

    if mode == "group_grid" or len(images) >= 4:
        # 2x2 群像参考网格 (1024x1280)
        tw, th = 512, 640
        canvas = Image.new("RGB", (tw * 2, th * 2), (24, 24, 24))
        for idx, im in enumerate(images[:4]):
            tile = fit_portrait_tile(im, tw, th)
            x = (idx % 2) * tw
            y = (idx // 2) * th
            canvas.paste(tile, (x, y))
        return canvas

    # 主角多角度横向参考卡 (2或3张并排：正面官方照 + 演讲/侧颜多角度)
    count = min(len(images), 3)
    tw, th = (512, 768) if count == 3 else (640, 896)
    canvas = Image.new("RGB", (tw * count, th), (24, 24, 24))
    for idx, im in enumerate(images[:count]):
        canvas.paste(fit_portrait_tile(im, tw, th), (idx * tw, 0))
    return canvas


def fetch_character(project_dir: Path, cid: str, cfg: dict[str, Any], force: bool = False) -> dict[str, Any]:
    cdir = project_dir / "characters" / cid
    cdir.mkdir(parents=True, exist_ok=True)
    primary_png = cdir / f"ref_{cid}.png"

    print(f"\n=== 获取人物多角度参考图: {cid} ({cfg['label']}) ===", flush=True)
    candidates: list[str] = list(cfg.get("files", []))
    target_count = int(cfg.get("target_count", 3))

    # 若预设文件不足目标数量，提前用 Wikimedia Search 补充候选
    seen_titles: set[str] = set()
    downloaded: list[tuple[str, Image.Image]] = []

    def try_titles(titles: list[str]) -> None:
        for title in titles:
            if len(downloaded) >= target_count:
                break
            norm = title.strip().replace("_", " ")
            if norm in seen_titles:
                continue
            seen_titles.add(norm)
            try:
                url, resolved_title = resolve_commons_file_url(title)
                if not url:
                    print(f"  [未找到] {title}", flush=True)
                    continue
                img = download_image(url)
                if img.width < 250 or img.height < 250:
                    print(f"  [分辨率过低跳过] {resolved_title} ({img.width}x{img.height})", flush=True)
                    continue
                downloaded.append((resolved_title, img))
                print(f"  [已下载 {len(downloaded)}/{target_count}] {resolved_title} ({img.width}x{img.height})", flush=True)
                time.sleep(0.4)
            except Exception as exc:
                print(f"  [下载失败跳过] {title}: {exc}", flush=True)

    try_titles(candidates)
    if len(downloaded) < target_count:
        for q in cfg.get("search_queries", []):
            if len(downloaded) >= target_count:
                break
            try:
                found = search_commons_files(q, limit=8)
                try_titles(found)
            except Exception as exc:
                print(f"  [搜索失败] {q}: {exc}", flush=True)

    if not downloaded:
        raise RuntimeError(f"未能为角色 {cid} 下载到任何有效参考图！")

    saved_files: list[str] = []
    # 保存各角度独立高清图（供人工筛选或单图精调）
    slot_names = [f"ref_{cid}_front.png", f"ref_{cid}_half.png", f"ref_{cid}_full.png", f"ref_{cid}_extra.png"]
    for idx, (title, img) in enumerate(downloaded):
        out_name = slot_names[idx] if idx < len(slot_names) else f"ref_{cid}_{idx+1:02d}.png"
        out_path = cdir / out_name
        if force or not out_path.exists():
            fit_portrait_tile(img, 896, 1152).save(out_path, format="PNG")
        saved_files.append(f"characters/{cid}/{out_name}")

    # 主参考图 ref_<id>.png：
    # - 群像 (democrats/republicans)：使用 2x2 拼图呈现4位代表人物
    # - 核心主角 (trump/jensen_huang/scott_bessent/marco_rubio/jd_vance)：使用多角度并排定妆卡
    #   同时保留 ref_<id>_front.png 作为单人正面特写备用
    if force or not primary_png.exists():
        composite = build_composite_reference([im for _, im in downloaded], mode=cfg["mode"])
        composite.save(primary_png, format="PNG")
    saved_files.insert(0, f"characters/{cid}/ref_{cid}.png")

    print(f"  [主锚定图就绪] {primary_png} (融合 {len(downloaded)} 张权威真图)", flush=True)
    return {
        "character_id": cid,
        "label": cfg["label"],
        "sources": [t for t, _ in downloaded],
        "saved_files": saved_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="从 Wikimedia Commons 抓取剧本项目七方角色的多角度高清真人参考图")
    parser.add_argument("--project-dir", required=True, help="剧本项目路径（如 /content/drive/MyDrive/AI_Video/projects/02_yongzheng_ep12_huang）")
    parser.add_argument("--characters", nargs="*", default=None, help="可选：仅抓取指定 character_id 列表")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有参考图")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    target_cids = args.characters if args.characters else list(CHARACTER_SOURCES.keys())

    report: list[dict[str, Any]] = []
    for cid in target_cids:
        if cid not in CHARACTER_SOURCES:
            print(f"[警告] 未在图源清单中找到角色: {cid}", file=sys.stderr)
            continue
        report.append(fetch_character(project_dir, cid, CHARACTER_SOURCES[cid], force=args.force))

    manifest_out = project_dir / "characters" / "refs_manifest.json"
    manifest_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n[全部完成] 已完成 {len(report)} 个角色的多角度高清参考图抓取，清单写入: {manifest_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
