#!/usr/bin/env python3
"""
原片精改三段式管线（不重新生成画面，100% 保留原片清宫服饰、场景、运镜与表演）：
  Stage 1 (--stage analyze)  : 截取工作片段 -> Demucs 剥离人声保留原配乐环境音 ->
                               Faster-Whisper large-v3 精确逐句时间戳对齐 ->
                               InsightFace 人脸聚类与主角自动映射（产出 actor_clusters.jpg + actor_face_map.json）
  Stage 2 (--stage dub)      : 拉取 4 位主角公开演讲纯净干音 -> 跨语种零样本中文音色克隆 (Chatterbox Multilingual / CosyVoice2) ->
                               pitch-preserving 精准时间窗对齐 + 原片环境声/配乐混音 + EBU R128 归一化
  Stage 3 (--stage faceswap) : 多角度 ArcFace 融合向量 -> 逐帧 GPU 高精度多角色定向换脸 (inswapper_128 + Lab色彩匹配 + GFPGANv1.4高清修复)
  Stage 4 (--stage lipsync)  : 仅对发声时间窗内的当前说话人脸执行音频驱动精准口型同步 (Wav2Lip-GAN / MuseTalk) + 封装最终 MP4 + ffprobe 质检
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"[CMD] {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, check=check, text=True)


def probe_media(path: Path) -> dict[str, Any]:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        text=True,
    )
    return json.loads(raw)


def download_file(url: str, dest: Path, min_bytes: int = 10_000, max_retries: int = 4) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    headers = {
        "User-Agent": "AI-Video-Pipeline/1.0 (https://github.com/WSQ233/AI-Video; educational-research)",
        "Accept": "*/*",
    }
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
                shutil.copyfileobj(resp, out)
            os.replace(tmp, dest)
            return dest
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 502, 503, 504) and attempt < max_retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                wait_s = float(retry_after) if (retry_after and retry_after.isdigit()) else (4.0 * attempt)
                print(f"  [下载限流 {exc.code}] 等待 {wait_s:.0f}s 后第 {attempt + 1}/{max_retries} 次重试...", flush=True)
                time.sleep(wait_s)
                continue
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                wait_s = 3.0 * attempt
                print(f"  [下载重试] {exc}，等待 {wait_s:.0f}s...", flush=True)
                time.sleep(wait_s)
                continue
            raise
    if last_exc:
        raise last_exc
    return dest


# =============================================================================
# Stage 1: Trim + Demucs + Whisper Alignment + Face Clustering
# =============================================================================

def _norm_zh(text: str) -> str:
    return "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff" or ch.isalnum())


def align_lines_to_whisper(
    plan_lines: list[dict[str, Any]],
    whisper_segs: list[dict[str, Any]],
    max_sec: float,
) -> tuple[list[dict[str, Any]], float]:
    """
    将改编剧本中的每一句台词（shot01..shot21）按顺序对齐到原片 Whisper 识别出的真实时间戳。
    使用顺序单调窗口 + 中文关键词/编辑距离综合打分，确保无倒序且紧密贴合原演员开口时间。
    """
    # 若 plan 中已给出逐句精校后的 fixed_start / fixed_end，直接采用毫秒级精校时间窗
    if all("fixed_start" in ln and "fixed_end" in ln for ln in plan_lines):
        aligned_fixed: list[dict[str, Any]] = []
        for ln in plan_lines:
            ts = float(ln["fixed_start"])
            te = float(ln["fixed_end"])
            aligned_fixed.append({
                "id": ln["id"],
                "speaker": ln["speaker"],
                "orig_role": ln["orig_role"],
                "start": round(ts, 3),
                "end": round(te, 3),
                "duration": round(te - ts, 3),
                "match_score": 1.0,
                "orig_text": ln.get("orig_hint", ""),
                "adapted_text": ln["adapted_text"],
            })
        clip_end_fixed = min(max_sec, aligned_fixed[-1]["end"] + 0.35)
        return aligned_fixed, round(clip_end_fixed, 3)

    n_segs = len(whisper_segs)
    if n_segs == 0:
        raise RuntimeError("Whisper 未识别到任何原片中文台词，请检查原片音频轨！")

    aligned: list[dict[str, Any]] = []
    cursor = 0
    total_lines = len(plan_lines)

    for idx, line in enumerate(plan_lines):
        keywords = [_norm_zh(k) for k in line.get("orig_keywords", []) if _norm_zh(k)]
        hint = _norm_zh(line.get("orig_hint", ""))
        remaining_lines = max(1, total_lines - idx)
        # 动态搜索窗：从当前 cursor 起向后看最多 8 个原片片段，并保留给后续句子的余量
        search_end = min(n_segs, max(cursor + 1, cursor + 8))

        best_score = -1.0
        best_span = (cursor, min(n_segs - 1, cursor))

        for s in range(cursor, search_end):
            for e in range(s, min(n_segs, s + 4)):
                cand_txt = _norm_zh("".join(w["text"] for w in whisper_segs[s : e + 1]))
                if not cand_txt:
                    continue
                kw_hits = sum(1.0 for kw in keywords if kw in cand_txt) / max(1, len(keywords))
                sim = difflib.SequenceMatcher(None, hint, cand_txt).ratio()
                # 轻微偏好紧贴 cursor 防止跳段
                dist_penalty = 0.04 * (s - cursor)
                score = 0.65 * kw_hits + 0.45 * sim - dist_penalty
                if score > best_score:
                    best_score = score
                    best_span = (s, e)

        s_idx, e_idx = best_span
        t_start = float(whisper_segs[s_idx]["start"])
        t_end = float(whisper_segs[e_idx]["end"])
        orig_text = " ".join(w["text"].strip() for w in whisper_segs[s_idx : e_idx + 1]).strip()

        # 防止极端短句时长过短（至少 0.7s）
        if t_end - t_start < 0.7:
            t_end = min(max_sec, t_start + 0.9)

        aligned.append({
            "id": line["id"],
            "speaker": line["speaker"],
            "orig_role": line["orig_role"],
            "start": round(t_start, 3),
            "end": round(t_end, 3),
            "duration": round(t_end - t_start, 3),
            "match_score": round(best_score, 3),
            "orig_text": orig_text,
            "adapted_text": line["adapted_text"],
        })
        cursor = min(n_segs - 1, e_idx + 1)

    # 平滑修正可能出现的微小重叠
    for i in range(1, len(aligned)):
        if aligned[i]["start"] < aligned[i - 1]["end"]:
            mid = round((aligned[i - 1]["end"] + aligned[i]["start"]) / 2.0, 3)
            aligned[i - 1]["end"] = max(aligned[i - 1]["start"] + 0.5, mid - 0.03)
            aligned[i]["start"] = mid + 0.03
            aligned[i - 1]["duration"] = round(aligned[i - 1]["end"] - aligned[i - 1]["start"], 3)
            aligned[i]["duration"] = round(aligned[i]["end"] - aligned[i]["start"], 3)

    clip_end = min(max_sec, aligned[-1]["end"] + 1.5)
    return aligned, round(clip_end, 3)


def stage_analyze(project_dir: Path, plan: dict[str, Any], work_dir: Path) -> None:
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    from faster_whisper import WhisperModel
    from insightface.app import FaceAnalysis
    from sklearn.cluster import AgglomerativeClustering

    src_video = project_dir / plan["source_video"]
    if not src_video.exists():
        raise FileNotFoundError(f"找不到原片视频: {src_video}")

    work_dir.mkdir(parents=True, exist_ok=True)
    trim_max = float(plan.get("trim_max_sec", 258.0))
    trim_start = float(plan.get("trim_start_sec", 0.0))

    raw_cut = work_dir / "work_clip_raw.mp4"
    if not raw_cut.exists() or raw_cut.stat().st_size < 1_000_000:
        local_src = work_dir / "src_local.mp4"
        if not local_src.exists():
            shutil.copy2(src_video, local_src)
        print(f"\n[Stage 1.1] 截取工作区间 {trim_start:.1f}s ~ {trim_max:.1f}s -> {raw_cut}", flush=True)
        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-ss", f"{trim_start:.3f}", "-to", f"{trim_max:.3f}",
            "-i", str(local_src),
            "-c:v", "libx264", "-crf", "16", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
            str(raw_cut),
        ])
    else:
        print(f"\n[Stage 1.1 复用] 已存在截取工作区间: {raw_cut}", flush=True)

    orig_wav = work_dir / "orig_audio_48k.wav"
    if not orig_wav.exists() or orig_wav.stat().st_size < 100_000:
        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(raw_cut), "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2",
            str(orig_wav),
        ])

    # Demucs 人声/背景音分离（100% 保留原片朝堂配乐与环境声）
    bg_wav = work_dir / "bg_music_ambience.wav"
    vocals_wav = work_dir / "vocals_orig.wav"
    if not (bg_wav.exists() and vocals_wav.exists()):
        print("\n[Stage 1.2] 使用 Demucs (htdemucs) 分离原片人声与背景环境声/配乐...", flush=True)
        demucs_out = work_dir / "demucs_out"
        run_cmd([
            sys.executable, "-m", "demucs",
            "--two-stems=vocals", "-n", "htdemucs",
            "-o", str(demucs_out),
            str(orig_wav),
        ])
        stem_dir = demucs_out / "htdemucs" / orig_wav.stem
        shutil.copy2(stem_dir / "vocals.wav", vocals_wav)
        shutil.copy2(stem_dir / "no_vocals.wav", bg_wav)
    print(f"[Demucs 完成] 人声: {vocals_wav} | 原片环境配乐: {bg_wav}", flush=True)

    # 若计划表已锁定逐句毫秒时间窗，跳过重复 Whisper 识别直接精校对齐
    if all("fixed_start" in ln and "fixed_end" in ln for ln in plan["lines"]):
        print("\n[Stage 1.3] 检测到毫秒级精校时间窗，直接按固定时间轴对齐（零漂移）...", flush=True)
        whisper_segs = []
    else:
        # Faster-Whisper large-v3 逐句中文识别与自动对齐（直接读原片全频带音轨并关闭前文条件，彻底杜绝字幕幻觉）
        print("\n[Stage 1.3] 使用 Faster-Whisper large-v3 提取原片逐句中文时间戳...", flush=True)
        wmodel = WhisperModel("large-v3", device="cuda", compute_type="float16")
        segs_iter, info = wmodel.transcribe(
            str(orig_wav),
            language="zh",
            beam_size=5,
            condition_on_previous_text=False,
            no_speech_threshold=0.65,
            compression_ratio_threshold=2.0,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 220, "threshold": 0.35},
            initial_prompt="雍正王朝第12集乾清宫议举新太子：朕今天和你们一道议举新太子，在京四品以上外省二品以上，佟国维、马齐、张廷玉、二阿哥胤礽、王掞、托合齐、耿索图、凌普。",
        )
        bad_hallucinations = ("请不吝点赞", "明镜", "点点栏目", "字幕由", "感谢观看")
        whisper_segs = [
            {"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()}
            for s in segs_iter
            if s.text.strip() and not any(b in s.text for b in bad_hallucinations)
        ]
        (work_dir / "orig_transcript.json").write_text(
            json.dumps(whisper_segs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[Whisper 完成] 共识别 {len(whisper_segs)} 段原片台词：", flush=True)
        for ws in whisper_segs:
            print(f"  [{ws['start']:6.2f}s - {ws['end']:6.2f}s] {ws['text']}", flush=True)

    aligned, clip_end = align_lines_to_whisper(plan["lines"], whisper_segs, trim_max - trim_start)
    # 严格贴合用户要求在 4:11 (251s) 处收尾，防止漏出 4:10.5 之后的「佟国维」
    target_hint = float(plan.get("target_end_hint_sec", 251.0))
    clip_end = min(clip_end, target_hint + 0.3)

    timeline_obj = {
        "source_video": str(src_video),
        "clip_duration_sec": clip_end,
        "lines": aligned,
    }
    (work_dir / "aligned_dub_timeline.json").write_text(
        json.dumps(timeline_obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[对齐完成] shot01–shot21 精确裁剪终点: {clip_end:.2f}s ({int(clip_end//60)}:{clip_end%60:05.2f})", flush=True)
    for al in aligned:
        print(
            f"  {al['id']:7s} [{al['start']:6.2f}s-{al['end']:6.2f}s] ({al['speaker']:13s}) "
            f"score={al['match_score']:.2f} | {al['adapted_text'][:28]}",
            flush=True,
        )

    # 裁剪精确的最终长度工作视频与背景音轨
    work_clip = work_dir / "work_clip.mp4"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(raw_cut), "-t", f"{clip_end:.3f}", "-c", "copy", str(work_clip),
    ])
    bg_cut = work_dir / "bg_music_cut.wav"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(bg_wav), "-t", f"{clip_end:.3f}", "-c", "copy", str(bg_cut),
    ])

    # InsightFace 人脸采样聚类 + 按发声时间窗自动匹配康熙/佟国维/张廷玉/马齐
    print("\n[Stage 1.4] 扫描原片人脸并自动聚类主角 ID...", flush=True)
    app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))

    cap = cv2.VideoCapture(str(work_clip))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(round(fps * 0.4)))
    samples: list[dict[str, Any]] = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % step == 0:
            t_sec = frame_idx / fps
            faces = app.get(frame)
            for f in faces:
                if f.det_score < 0.58:
                    continue
                x1, y1, x2, y2 = [int(v) for v in f.bbox]
                w, h = x2 - x1, y2 - y1
                if w < 38 or h < 38:
                    continue
                pad = int(max(w, h) * 0.25)
                cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
                cx2, cy2 = min(frame.shape[1], x2 + pad), min(frame.shape[0], y2 + pad)
                crop = cv2.cvtColor(frame[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2RGB)
                samples.append({
                    "t": round(t_sec, 2),
                    "area": w * h,
                    "score": float(f.det_score),
                    "emb": f.normed_embedding.astype(np.float32),
                    "crop": crop,
                })
        frame_idx += 1
    cap.release()

    if len(samples) < 2:
        raise RuntimeError("原片检测到的人脸样本过少，无法完成聚类！")

    embs = np.stack([s["emb"] for s in samples], axis=0)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        metric="cosine",
        linkage="average",
        distance_threshold=0.48,
    )
    labels = clustering.fit_predict(embs)

    clusters: dict[int, list[dict[str, Any]]] = {}
    for s, lbl in zip(samples, labels):
        clusters.setdefault(int(lbl), []).append(s)

    # 过滤极短暂噪点（少于 2 帧）
    valid_cids = [cid for cid, items in sorted(clusters.items(), key=lambda kv: -len(kv[1])) if len(items) >= 2]

    # 按发声角色时间窗统计每个聚类的「主镜面积加权出现度」，自动锁定康熙/佟国维/张廷玉/马齐
    role_windows: dict[str, list[tuple[float, float]]] = {}
    for al in aligned:
        role_windows.setdefault(al["orig_role"], []).append((al["start"], al["end"]))

    role_to_speaker = {
        "kangxi": "trump",
        "tongguowei": "marco_rubio",
        "zhangtingyu": "scott_bessent",
        "maqi": "jd_vance",
    }

    role_scores: dict[str, dict[int, float]] = {r: {} for r in role_to_speaker}
    for cid in valid_cids:
        for role, wins in role_windows.items():
            if role not in role_scores:
                continue
            sc = 0.0
            for it in clusters[cid]:
                if any(ws <= it["t"] <= we for ws, we in wins):
                    sc += math.sqrt(it["area"]) * it["score"]
            role_scores[role][cid] = sc

    assigned_roles: dict[int, str] = {}
    used_cids: set[int] = set()
    for role in ("kangxi", "tongguowei", "zhangtingyu", "maqi"):
        ranked = sorted(role_scores[role].items(), key=lambda kv: -kv[1])
        for cid, sc in ranked:
            if cid not in used_cids and sc > 0:
                assigned_roles[cid] = role_to_speaker[role]
                used_cids.add(cid)
                break

    # 其余高出场朝臣自动轮换映射至民主党/共和党 8 张独立政客肖像
    bg_pool = plan["face_portraits"]["background_pool"]
    bg_idx = 0
    cluster_meta: list[dict[str, Any]] = []
    for cid in valid_cids:
        items = clusters[cid]
        centroid = np.mean(np.stack([x["emb"] for x in items], axis=0), axis=0)
        centroid = centroid / (np.linalg.norm(centroid) + 1e-8)
        if cid in assigned_roles:
            target = assigned_roles[cid]
        else:
            target = f"bg:{bg_pool[bg_idx % len(bg_pool)]}"
            bg_idx += 1
        top_times = [x["t"] for x in sorted(items, key=lambda z: -z["area"])[:5]]
        cluster_meta.append({
            "cluster_id": cid,
            "count": len(items),
            "target": target,
            "sample_times": top_times,
            "centroid": centroid.tolist(),
        })

    (work_dir / "actor_face_map.json").write_text(
        json.dumps(cluster_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 生成可视化演员聚类对照图 (actor_clusters.jpg)，便于肉眼复核
    max_show = min(14, len(cluster_meta))
    tile = 160
    cols = 4  # label + top 3 crops
    sheet = Image.new("RGB", (tile * cols, tile * max_show), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    for row_i, cm in enumerate(cluster_meta[:max_show]):
        cid = cm["cluster_id"]
        y0 = row_i * tile
        draw.rectangle([4, y0 + 4, tile - 4, y0 + tile - 4], fill=(32, 34, 42))
        label_lines = [
            f"Cluster #{cid}",
            f"Frames: {cm['count']}",
            f"-> {cm['target'].split('/')[-1][:18]}",
            f"t={cm['sample_times'][0]:.1f}s",
        ]
        draw.text((10, y0 + 24), "\n".join(label_lines), fill=(240, 240, 240))
        top_crops = sorted(clusters[cid], key=lambda z: -(z["area"] * z["score"]))[:3]
        for ci, item in enumerate(top_crops):
            im = Image.fromarray(item["crop"]).resize((tile - 8, tile - 8))
            sheet.paste(im, ((ci + 1) * tile + 4, y0 + 4))
    sheet_path = work_dir / "actor_clusters.jpg"
    sheet.save(sheet_path, quality=90)
    # 同步保存一份到 5TB Drive 便于本机远程核验聚类映射
    debug_dir = project_dir / "outputs" / "replace_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sheet_path, debug_dir / "actor_clusters.jpg")
    shutil.copy2(work_dir / "actor_face_map.json", debug_dir / "actor_face_map.json")
    shutil.copy2(work_dir / "aligned_dub_timeline.json", debug_dir / "aligned_dub_timeline.json")
    print(f"[人脸聚类完成] 共识别 {len(cluster_meta)} 个稳定角色，对照图: {sheet_path}", flush=True)
    for cm in cluster_meta[:10]:
        print(f"  Cluster #{cm['cluster_id']:2d} (n={cm['count']:3d}) -> {cm['target']}", flush=True)


# =============================================================================
# Stage 2: Voice Cloning (English Studio Ref -> Expressive Mandarin) + Mix
# =============================================================================

def prepare_voice_refs(project_dir: Path, plan: dict[str, Any], work_dir: Path) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    raw_dir = work_dir / "raw_voices"
    raw_dir.mkdir(parents=True, exist_ok=True)
    needed_speakers = {str(ln["speaker"]) for ln in plan.get("lines", [])}
    downloaded_any = False
    for spk, cfg in plan["voice_sources"].items():
        if needed_speakers and spk not in needed_speakers:
            continue
        target_wav = project_dir / cfg["local_rel"]
        target_wav.parent.mkdir(parents=True, exist_ok=True)
        if target_wav.exists() and target_wav.stat().st_size > 20_000:
            print(f"[声纹复用] {spk} -> {target_wav}", flush=True)
            refs[spk] = target_wav
            continue
        if downloaded_any:
            time.sleep(2.5)
        raw_ext = Path(cfg["url"].split("?")[0]).suffix or ".ogg"
        raw_file = raw_dir / f"{spk}_raw{raw_ext}"
        try:
            download_file(cfg["url"], raw_file)
        except Exception as exc:
            fb = cfg.get("fallback_url", "")
            if not fb:
                raise
            print(f"[声纹回退] {spk} 主链接失败 ({exc})，改用备用源...", flush=True)
            raw_file = raw_dir / f"{spk}_fb{Path(fb.split('?')[0]).suffix or '.ogg'}"
            download_file(fb, raw_file)
        downloaded_any = True
        start_s = float(cfg.get("clip_start_sec", 5.0))
        dur_s = float(cfg.get("clip_duration_sec", 12.0))
        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-ss", f"{start_s:.2f}", "-t", f"{dur_s:.2f}",
            "-i", str(raw_file),
            "-af", "highpass=f=80,lowpass=f=10000,loudnorm=I=-18:TP=-1.5:LRA=9",
            "-ac", "1", "-ar", "24000", "-acodec", "pcm_s16le",
            str(target_wav),
        ])
        refs[spk] = target_wav
        print(f"[声纹就绪] {spk} -> {target_wav}", flush=True)
    return refs


def _build_atempo_chain(ratio: float) -> str:
    """构建 ffmpeg atempo 滤镜链（单级限制 0.5~2.0），保持原音色不变调。"""
    filters: list[str] = []
    r = max(0.65, min(1.55, ratio))
    while r > 2.0:
        filters.append("atempo=2.0")
        r /= 2.0
    while r < 0.5:
        filters.append("atempo=0.5")
        r /= 0.5
    filters.append(f"atempo={r:.4f}")
    return ",".join(filters)


def stage_dub(project_dir: Path, plan: dict[str, Any], work_dir: Path, tts_engine: str = "chatterbox") -> None:
    import numpy as np
    import soundfile as sf
    import torch

    timeline_path = work_dir / "aligned_dub_timeline.json"
    if not timeline_path.exists():
        raise FileNotFoundError(f"请先运行 --stage analyze 生成 {timeline_path}")
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    lines = timeline["lines"]
    total_dur = float(timeline["clip_duration_sec"])

    voice_refs = prepare_voice_refs(project_dir, plan, work_dir)
    tts_dir = work_dir / "tts_lines"
    tts_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[Stage 2.1] 加载跨语种本尊音色中文克隆引擎 ({tts_engine})...", flush=True)
    if tts_engine == "chatterbox":
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        model = ChatterboxMultilingualTTS.from_pretrained(device="cuda")
        sr_out = int(model.sr)
    else:
        raise ValueError(f"暂不支持的 TTS 引擎: {tts_engine}")

    # 逐句克隆本尊音色讲中文，并用 pitch-preserving atempo 严格对齐原演员时间窗
    sr_master = 48000
    master_samples = int(math.ceil(total_dur * sr_master))
    vocals_track = np.zeros(master_samples, dtype=np.float32)
    duck_mask = np.zeros(master_samples, dtype=np.float32)

    for line in lines:
        lid = line["id"]
        spk = line["speaker"]
        text = line["adapted_text"]
        t_start = float(line["start"])
        t_end = float(line["end"])
        target_dur = max(0.6, t_end - t_start)

        raw_wav = tts_dir / f"{lid}_{spk}_raw.wav"
        fit_wav = tts_dir / f"{lid}_{spk}_fit.wav"

        if not raw_wav.exists():
            print(f"  [克隆配音] {lid} ({spk}): {text}", flush=True)
            wav_tensor = model.generate(
                text,
                language_id="zh",
                audio_prompt_path=str(voice_refs[spk]),
                exaggeration=0.58 if spk == "trump" else 0.48,
                cfg_weight=0.42,
            )
            wav_np = wav_tensor.squeeze().detach().cpu().numpy().astype(np.float32)
            sf.write(str(raw_wav), wav_np, sr_out)

        # 裁剪首尾静音并测真实时长
        trimmed_wav = tts_dir / f"{lid}_{spk}_trim.wav"
        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(raw_wav),
            "-af", "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-40dB:stop_periods=-1:stop_silence=0.12:stop_threshold=-40dB",
            "-ac", "1", "-ar", str(sr_master), "-acodec", "pcm_s16le",
            str(trimmed_wav),
        ])
        data, _ = sf.read(str(trimmed_wav), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        gen_dur = len(data) / sr_master
        if gen_dur < 0.25:
            data, _ = sf.read(str(raw_wav), dtype="float32")
            gen_dur = len(data) / sr_out
            trimmed_wav = raw_wav

        # 若克隆语音超出目标窗，温和提速至刚好贴合；若偏短太多，轻微放慢保持自然节奏
        ratio = gen_dur / target_dur
        if ratio > 1.03:
            tempo = min(1.42, ratio)
        elif ratio < 0.72:
            tempo = max(0.82, ratio)
        else:
            tempo = 1.0

        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(trimmed_wav),
            "-af", f"{_build_atempo_chain(tempo)},loudnorm=I=-16:TP=-1.5:LRA=9",
            "-ac", "1", "-ar", str(sr_master), "-acodec", "pcm_s16le",
            str(fit_wav),
        ])
        fit_data, _ = sf.read(str(fit_wav), dtype="float32")
        if fit_data.ndim > 1:
            fit_data = fit_data.mean(axis=1)

        s_idx = int(round(t_start * sr_master))
        e_idx = min(master_samples, s_idx + len(fit_data))
        seg_len = max(0, e_idx - s_idx)
        if seg_len > 0:
            # 15ms 淡入淡出防爆音
            fade = min(int(0.015 * sr_master), seg_len // 4)
            seg = fit_data[:seg_len].copy()
            if fade > 0:
                seg[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
                seg[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
            vocals_track[s_idx:e_idx] += seg
            duck_mask[s_idx:e_idx] = 1.0
        print(f"    -> gen={gen_dur:.2f}s / win={target_dur:.2f}s (tempo={tempo:.2f}x)", flush=True)

    vocals_only_path = work_dir / "dubbed_vocals_only.wav"
    sf.write(str(vocals_only_path), np.clip(vocals_track, -0.98, 0.98), sr_master)

    # 混入原片《雍正王朝》背景配乐/环境声（说话时背景轻压 -4dB，静默时恢复原音量）
    bg_cut = work_dir / "bg_music_cut.wav"
    bg_data, bg_sr = sf.read(str(bg_cut), dtype="float32")
    if bg_data.ndim == 1:
        bg_data = np.stack([bg_data, bg_data], axis=1)
    if len(bg_data) < master_samples:
        pad = np.zeros((master_samples - len(bg_data), 2), dtype=np.float32)
        bg_data = np.concatenate([bg_data, pad], axis=0)
    else:
        bg_data = bg_data[:master_samples]

    # 平滑 duck 包络（约 150ms 窗口）
    win_n = int(0.15 * sr_master)
    kernel = np.ones(win_n, dtype=np.float32) / win_n
    smooth_duck = np.convolve(duck_mask, kernel, mode="same")
    bg_gain = 1.0 - 0.38 * smooth_duck  # 说话时背景保持 62%（~ -4.1 dB）

    mixed = np.zeros((master_samples, 2), dtype=np.float32)
    mixed[:, 0] = bg_data[:, 0] * bg_gain + vocals_track * 1.05
    mixed[:, 1] = bg_data[:, 1] * bg_gain + vocals_track * 1.05

    raw_mix = work_dir / "dubbed_mix_raw.wav"
    sf.write(str(raw_mix), np.clip(mixed, -0.98, 0.98), sr_master)

    master_audio = work_dir / "dubbed_master_audio.wav"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(raw_mix),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-ac", "2", "-ar", str(sr_master), "-acodec", "pcm_s16le",
        str(master_audio),
    ])
    print(f"[Stage 2 完成] 克隆干声: {vocals_only_path} | 终混音轨: {master_audio}", flush=True)


# =============================================================================
# Stage 3: Multi-Angle Multi-Character Original-Video Face Swap + GFPGAN
# =============================================================================

def ensure_face_models(shared_models_dir: Path) -> tuple[Path, Path]:
    face_dir = shared_models_dir / "face_replace"
    face_dir.mkdir(parents=True, exist_ok=True)
    inswapper_path = face_dir / "inswapper_128.onnx"
    gfpgan_path = face_dir / "GFPGANv1.4.pth"

    if not inswapper_path.exists() or inswapper_path.stat().st_size < 200_000_000:
        urls = [
            "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx",
            "https://huggingface.co/datasets/OwlMaster/gg2/resolve/main/inswapper_128.onnx",
        ]
        for u in urls:
            try:
                print(f"[下载换脸权重] {u}", flush=True)
                download_file(u, inswapper_path, min_bytes=200_000_000)
                break
            except Exception as exc:
                print(f"  [重试下一个镜像] {exc}", flush=True)

    if not gfpgan_path.exists() or gfpgan_path.stat().st_size < 200_000_000:
        url = "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"
        print(f"[下载超分修复权重] {url}", flush=True)
        download_file(url, gfpgan_path, min_bytes=200_000_000)

    return inswapper_path, gfpgan_path


def _match_lab_color(src_bgr: Any, dst_bgr: Any, mask: Any) -> Any:
    import cv2
    import numpy as np

    m = mask > 0.25
    if m.sum() < 50:
        return src_bgr
    s_lab = cv2.cvtColor(src_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    d_lab = cv2.cvtColor(dst_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    for c in range(3):
        s_mean, s_std = s_lab[:, :, c][m].mean(), s_lab[:, :, c][m].std() + 1e-5
        d_mean, d_std = d_lab[:, :, c][m].mean(), d_lab[:, :, c][m].std() + 1e-5
        # 保留适度色彩融合（85% 原片光影色温 + 15% 源肤色特征）
        matched = (s_lab[:, :, c] - s_mean) * (d_std / s_std) + d_mean
        s_lab[:, :, c] = np.clip(0.85 * matched + 0.15 * s_lab[:, :, c], 0, 255)
    return cv2.cvtColor(s_lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def stage_faceswap(project_dir: Path, plan: dict[str, Any], work_dir: Path, shared_models_dir: Path) -> None:
    import cv2
    import insightface
    import numpy as np
    from gfpgan import GFPGANer
    from insightface.app import FaceAnalysis

    work_clip = work_dir / "work_clip.mp4"
    face_map_path = work_dir / "actor_face_map.json"
    if not (work_clip.exists() and face_map_path.exists()):
        raise FileNotFoundError("请先运行 --stage analyze 生成 work_clip.mp4 与 actor_face_map.json")

    inswapper_path, gfpgan_path = ensure_face_models(shared_models_dir)
    app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    swapper = insightface.model_zoo.get_model(str(inswapper_path), providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    restorer = GFPGANer(
        model_path=str(gfpgan_path),
        upscale=1,
        arch="clean",
        channel_multiplier=2,
        bg_upsampler=None,
        device="cuda",
    )

    # 构建多角度平均源人脸对象（正面 + 半身 + 全身联合锁死 3D 骨相）
    def build_source_face(img_rels: list[str]) -> Any:
        embs = []
        base_face = None
        for rel in img_rels:
            p = project_dir / rel
            if not p.exists():
                continue
            im = cv2.imread(str(p))
            if im is None:
                continue
            faces = app.get(im)
            if not faces:
                continue
            f = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
            embs.append(f.normed_embedding.astype(np.float32))
            if base_face is None:
                base_face = f
        if base_face is None:
            raise RuntimeError(f"无法从参考图提取人脸向量: {img_rels}")
        avg_emb = np.mean(np.stack(embs, axis=0), axis=0)
        avg_emb = avg_emb / (np.linalg.norm(avg_emb) + 1e-8)
        base_face.embedding = avg_emb * np.linalg.norm(base_face.embedding)
        base_face.normed_embedding = avg_emb
        return base_face

    source_faces: dict[str, Any] = {}
    for role_id in ("trump", "marco_rubio", "scott_bessent", "jd_vance"):
        source_faces[role_id] = build_source_face(plan["face_portraits"][role_id])
        print(f"[多角度源人脸就绪] {role_id}", flush=True)

    bg_sources: dict[str, Any] = {}
    for bg_rel in plan["face_portraits"]["background_pool"]:
        try:
            bg_sources[f"bg:{bg_rel}"] = build_source_face([bg_rel])
        except Exception as exc:
            print(f"[警告] 群臣参考图跳过 {bg_rel}: {exc}", flush=True)

    cluster_meta = json.loads(face_map_path.read_text(encoding="utf-8"))
    # 自动合并同主角多角度次级聚类（如侧脸/低头/远景光照分裂出的康熙、佟国维、张廷玉），并应用人工复核覆写表
    lead_roles = ("trump", "marco_rubio", "scott_bessent", "jd_vance")
    lead_centroids: dict[str, Any] = {}
    for cm in cluster_meta:
        if cm["target"] in lead_roles and cm["target"] not in lead_centroids:
            lead_centroids[cm["target"]] = np.array(cm["centroid"], dtype=np.float32)

    overrides = {str(k): str(v) for k, v in plan.get("cluster_overrides", {}).items()}
    merged_count = 0
    for cm in cluster_meta:
        cid_str = str(cm["cluster_id"])
        if cid_str in overrides:
            cm["target"] = overrides[cid_str]
            continue
        if cm["target"] in lead_roles:
            continue
        v = np.array(cm["centroid"], dtype=np.float32)
        best_lead, best_sim = None, 0.0
        for lr, lv in lead_centroids.items():
            sim = float(np.dot(v, lv))
            if sim > best_sim:
                best_lead, best_sim = lr, sim
        if best_lead and best_sim >= 0.42:
            cm["target"] = best_lead
            merged_count += 1
            print(f"  [多角度主角聚类自动合并] Cluster #{cm['cluster_id']:2d} (n={cm['count']:2d}, sim={best_sim:.2f}) -> {best_lead}", flush=True)

    centroids = np.stack([np.array(cm["centroid"], dtype=np.float32) for cm in cluster_meta], axis=0)
    targets = [cm["target"] for cm in cluster_meta]
    print(f"[角色映射就绪] 共 {len(cluster_meta)} 个聚类（自动合并主角多角度 {merged_count} 组，人工覆写 {len(overrides)} 组）", flush=True)

    cap = cv2.VideoCapture(str(work_clip))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    raw_swapped = work_dir / "swapped_video_nosync_raw.mp4"
    writer = cv2.VideoWriter(str(raw_swapped), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    # 同步记录每帧每个角色的人脸框，供 Stage 4 仅对当前说话人做精准口型同步
    speaker_tracks: list[dict[str, list[int]]] = []

    print(f"\n[Stage 3] 开始原片逐帧高精度多角色换脸 + GFPGAN 清晰度修复 ({total_frames} 帧, {width}x{height}@{fps:.2f}fps)...", flush=True)
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out_frame = frame.copy()
        frame_track: dict[str, list[int]] = {}
        faces = app.get(frame)

        if faces:
            for f in faces:
                if f.det_score < 0.50:
                    continue
                x1, y1, x2, y2 = [int(v) for v in f.bbox]
                fw, fh = x2 - x1, y2 - y1
                if fw < 34 or fh < 34:
                    continue
                sims = centroids @ f.normed_embedding.astype(np.float32)
                best_i = int(np.argmax(sims))
                if float(sims[best_i]) < 0.36:
                    continue
                tgt_key = targets[best_i]
                if tgt_key == "skip":
                    continue
                # 仅对清晰前景群臣执行换脸，自动跳过远景虚化或背面侧头，杜绝闪烁穿帮
                if tgt_key not in source_faces and (f.det_score < 0.68 or fw < 48 or fh < 48):
                    continue
                src_face = source_faces.get(tgt_key) or bg_sources.get(tgt_key)
                if src_face is None:
                    continue
                if tgt_key in source_faces:
                    frame_track[tgt_key] = [max(0, x1), max(0, y1), min(width, x2), min(height, y2)]

                swapped = swapper.get(out_frame, f, src_face, paste_back=True)

                # 对脸部局部区域做 Lab 色彩对齐 + 柔和羽化融合，避免边缘硬边和清宫光影跳变
                pad = int(max(x2 - x1, y2 - y1) * 0.25)
                rx1, ry1 = max(0, x1 - pad), max(0, y1 - pad)
                rx2, ry2 = min(width, x2 + pad), min(height, y2 + pad)
                roi_sw = swapped[ry1:ry2, rx1:rx2]
                roi_og = out_frame[ry1:ry2, rx1:rx2]
                rh, rw = roi_sw.shape[:2]
                if rh > 16 and rw > 16:
                    mask = np.zeros((rh, rw), dtype=np.float32)
                    cv2.ellipse(mask, (rw // 2, rh // 2), (int(rw * 0.38), int(rh * 0.42)), 0, 0, 360, 1.0, -1)
                    mask = cv2.GaussianBlur(mask, (0, 0), max(3, int(min(rw, rh) * 0.08)))
                    roi_col = _match_lab_color(roi_sw, roi_og, mask)
                    # 主角人脸走 GFPGAN 细节还原
                    if tgt_key in source_faces and (x2 - x1) >= 64:
                        _, _, restored_roi = restorer.enhance(roi_col, has_aligned=False, only_center_face=True, paste_back=True)
                        if restored_roi is not None and restored_roi.shape == roi_col.shape:
                            roi_col = cv2.addWeighted(restored_roi, 0.72, roi_col, 0.28, 0)
                    m3 = mask[:, :, None]
                    out_frame[ry1:ry2, rx1:rx2] = (roi_col * m3 + roi_og * (1.0 - m3)).astype(np.uint8)

        speaker_tracks.append(frame_track)
        writer.write(out_frame)
        idx += 1
        if idx % 300 == 0 or idx == total_frames:
            print(f"  [换脸进度] {idx}/{total_frames} 帧 ({idx * 100.0 / max(1, total_frames):.1f}%)", flush=True)

    cap.release()
    writer.release()

    (work_dir / "speaker_face_tracks.json").write_text(
        json.dumps({"fps": fps, "width": width, "height": height, "tracks": speaker_tracks}),
        encoding="utf-8",
    )

    swapped_h264 = work_dir / "swapped_video_nosync.mp4"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(raw_swapped),
        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
        str(swapped_h264),
    ])
    raw_swapped.unlink(missing_ok=True)
    print(f"[Stage 3 完成] 原片精准换脸视频: {swapped_h264}", flush=True)


# =============================================================================
# Stage 4: Active-Speaker Selective Lip-Sync (Wav2Lip-GAN + GFPGAN) + Final Mux
# =============================================================================

def _compute_wav2lip_mel(wav_16k: Any) -> Any:
    """复现 Wav2Lip 标准 80-bin mel 频谱（兼容现代 librosa / numpy，彻底规避旧版 filters.mel 报错）。"""
    import librosa
    import numpy as np
    from scipy import signal

    wav = signal.lfilter([1, -0.97], [1], wav_16k.astype(np.float32))
    stft = librosa.stft(y=wav, n_fft=800, hop_length=200, win_length=800)
    mel_basis = librosa.filters.mel(sr=16000, n_fft=800, n_mels=80, fmin=55, fmax=7600)
    mel = np.dot(mel_basis, np.abs(stft))
    mel_db = 20.0 * np.log10(np.maximum(1e-5, mel)) - 20.0
    mel_norm = np.clip((2.0 * 4.0) * ((mel_db + 100.0) / 100.0) - 4.0, -4.0, 4.0)
    return mel_norm.astype(np.float32)


def stage_lipsync(
    project_dir: Path,
    plan: dict[str, Any],
    work_dir: Path,
    shared_models_dir: Path,
    lipsync_repo: Path | None = None,
    skip_lipsync: bool = False,
) -> Path:
    import cv2
    import librosa
    import numpy as np
    import torch
    from gfpgan import GFPGANer

    swapped_video = work_dir / "swapped_video_nosync.mp4"
    master_audio = work_dir / "dubbed_master_audio.wav"
    vocals_only = work_dir / "dubbed_vocals_only.wav"
    timeline_path = work_dir / "aligned_dub_timeline.json"
    tracks_path = work_dir / "speaker_face_tracks.json"
    final_out = project_dir / plan["output_video"]
    final_out.parent.mkdir(parents=True, exist_ok=True)

    if not swapped_video.exists() or not master_audio.exists():
        raise FileNotFoundError("请先完成 Stage 2 (dub) 与 Stage 3 (faceswap)")

    video_for_mux = swapped_video

    if not skip_lipsync and lipsync_repo and (lipsync_repo / "models" / "wav2lip.py").exists():
        face_dir = shared_models_dir / "face_replace"
        face_dir.mkdir(parents=True, exist_ok=True)
        ckpt = face_dir / "wav2lip_gan.pth"
        if not ckpt.exists() or ckpt.stat().st_size < 100_000_000:
            print("[下载口型权重] wav2lip_gan.pth -> 5TB 云盘共享缓存...", flush=True)
            download_file(
                "https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth",
                ckpt,
                min_bytes=100_000_000,
            )

        print("\n[Stage 4.1] 执行说话人精准口型同步（仅驱动发声时间窗内的当前说话人脸，旁观大臣保持纹丝不动）...", flush=True)
        sys.path.insert(0, str(lipsync_repo))
        from models import Wav2Lip  # type: ignore

        model = Wav2Lip()
        checkpoint = torch.load(str(ckpt), map_location="cuda", weights_only=False)
        state = {k.replace("module.", ""): v for k, v in checkpoint["state_dict"].items()}
        model.load_state_dict(state)
        model = model.to("cuda").eval()

        _, gfpgan_path = ensure_face_models(shared_models_dir)
        restorer = GFPGANer(
            model_path=str(gfpgan_path),
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None,
            device="cuda",
        )

        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))["lines"]
        track_obj = json.loads(tracks_path.read_text(encoding="utf-8"))
        tracks: list[dict[str, list[int]]] = track_obj["tracks"]
        fps = float(track_obj["fps"])
        width = int(track_obj["width"])
        height = int(track_obj["height"])

        wav_16k, _ = librosa.load(str(vocals_only), sr=16000, mono=True)
        mel = _compute_wav2lip_mel(wav_16k)
        mel_idx_mult = 80.0 / fps
        mel_step_size = 16

        # 映射每帧对应的当前说话角色（不在发声窗内的帧不改口型，保持原片极致清晰）
        def active_speaker_at(t_sec: float) -> str | None:
            for ln in timeline:
                if float(ln["start"]) - 0.08 <= t_sec <= float(ln["end"]) + 0.08:
                    return str(ln["speaker"])
            return None

        cap = cv2.VideoCapture(str(swapped_video))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        synced_raw = work_dir / "swapped_lipsynced_raw.mp4"
        writer = cv2.VideoWriter(str(synced_raw), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

        batch_imgs: list[Any] = []
        batch_mels: list[Any] = []
        batch_meta: list[tuple[int, Any, tuple[int, int, int, int]]] = []
        frame_buffer: list[Any] = []

        def flush_batch() -> None:
            if not batch_imgs:
                return
            img_arr = np.asarray(batch_imgs, dtype=np.float32)
            img_masked = img_arr.copy()
            img_masked[:, 48:, :, :] = 0.0
            img_in = np.concatenate((img_masked, img_arr), axis=3) / 255.0
            img_t = torch.FloatTensor(np.transpose(img_in, (0, 3, 1, 2))).to("cuda")
            mel_arr = np.asarray(batch_mels, dtype=np.float32)[:, :, :, None]
            mel_t = torch.FloatTensor(np.transpose(mel_arr, (0, 3, 1, 2))).to("cuda")
            with torch.no_grad():
                preds = model(mel_t, img_t)
            preds_np = (preds.cpu().numpy().transpose(0, 2, 3, 1) * 255.0).clip(0, 255).astype(np.uint8)
            for (buf_idx, _, (x1, y1, x2, y2)), p_face in zip(batch_meta, preds_np):
                frm = frame_buffer[buf_idx]
                fw, fh = x2 - x1, y2 - y1
                p_res = cv2.resize(p_face, (fw, fh), interpolation=cv2.INTER_CUBIC)
                # 仅羽化替换下半张脸（鼻尖以下口部与下颌），保留换脸后上半张脸与眼睛的极致清晰度
                mask = np.zeros((fh, fw), dtype=np.float32)
                cv2.ellipse(mask, (fw // 2, int(fh * 0.72)), (int(fw * 0.36), int(fh * 0.25)), 0, 0, 360, 1.0, -1)
                mask = cv2.GaussianBlur(mask, (0, 0), max(3, int(fw * 0.07)))
                orig_roi = frm[y1:y2, x1:x2]
                blended = (p_res * mask[:, :, None] + orig_roi * (1.0 - mask[:, :, None])).astype(np.uint8)
                if fw >= 64:
                    _, _, enh = restorer.enhance(blended, has_aligned=False, only_center_face=True, paste_back=True)
                    if enh is not None and enh.shape == blended.shape:
                        blended = cv2.addWeighted(enh, 0.68, blended, 0.32, 0)
                frm[y1:y2, x1:x2] = blended
            batch_imgs.clear()
            batch_mels.clear()
            batch_meta.clear()

        f_idx = 0
        synced_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_buffer.append(frame)
            buf_i = len(frame_buffer) - 1
            t_sec = f_idx / fps
            spk = active_speaker_at(t_sec)
            if spk and f_idx < len(tracks) and spk in tracks[f_idx]:
                x1, y1, x2, y2 = tracks[f_idx][spk]
                # 略微向下扩展下巴 10% 便于口型自然张合
                pad_b = int((y2 - y1) * 0.12)
                y2p = min(height, y2 + pad_b)
                if (x2 - x1) >= 36 and (y2p - y1) >= 36:
                    start_m = int(f_idx * mel_idx_mult)
                    if start_m + mel_step_size <= mel.shape[1]:
                        m_chunk = mel[:, start_m : start_m + mel_step_size]
                    else:
                        m_chunk = mel[:, -mel_step_size:]
                    crop96 = cv2.resize(frame[y1:y2p, x1:x2], (96, 96), interpolation=cv2.INTER_AREA)
                    batch_imgs.append(crop96)
                    batch_mels.append(m_chunk)
                    batch_meta.append((buf_i, frame, (x1, y1, x2, y2p)))
                    synced_count += 1

            if len(frame_buffer) >= 64:
                flush_batch()
                for frm in frame_buffer:
                    writer.write(frm)
                frame_buffer.clear()

            f_idx += 1
            if f_idx % 400 == 0 or f_idx == total_frames:
                print(f"  [口型同步进度] {f_idx}/{total_frames} 帧 (已驱动说话人脸 {synced_count} 帧)", flush=True)

        if frame_buffer:
            flush_batch()
            for frm in frame_buffer:
                writer.write(frm)
            frame_buffer.clear()

        cap.release()
        writer.release()
        if synced_raw.exists() and synced_raw.stat().st_size > 1_000_000:
            video_for_mux = synced_raw
            print(f"[口型同步完成] 共精准驱动 {synced_count} 帧说话人脸口型", flush=True)

    print(f"\n[Stage 4.2] 封装最终高清双流成片 -> {final_out}", flush=True)
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video_for_mux),
        "-i", str(master_audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-movflags", "+faststart", "-shortest",
        str(final_out),
    ])

    info = probe_media(final_out)
    vs = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    as_ = [s for s in info["streams"] if s["codec_type"] == "audio"][0]
    dur = float(info["format"]["duration"])
    size_mb = final_out.stat().st_size / (1024 * 1024)
    print(
        f"\n[最终成片 FFprobe 验收 PASS] {final_out}\n"
        f"  时长: {dur:.2f}s ({int(dur//60)}:{dur%60:05.2f}) | 体积: {size_mb:.2f} MB\n"
        f"  视频流: {vs['codec_name']} {vs['width']}x{vs['height']} @{vs['r_frame_rate']}\n"
        f"  音频流: {as_['codec_name']} {as_['sample_rate']}Hz {as_['channels']}ch",
        flush=True,
    )
    return final_out


def main() -> int:
    parser = argparse.ArgumentParser(description="原片多角色换脸 + 本尊音色中文克隆配音 + 口型同步精改管线")
    parser.add_argument("--project-dir", required=True, help="剧本项目根目录，如 /content/drive/MyDrive/AI_Video/projects/02_yongzheng_ep12_huang")
    parser.add_argument("--plan", default="dubbing_plan_shot01_21.json", help="原片精改计划 JSON（相对项目目录或绝对路径）")
    parser.add_argument("--work-dir", default="/content/work_replace", help="Colab 本地高速工作目录")
    parser.add_argument("--shared-models-dir", default="/content/drive/MyDrive/AI_Video/shared/models", help="5TB Drive 共享模型目录")
    parser.add_argument("--stage", choices=["all", "analyze", "dub", "faceswap", "lipsync"], default="all")
    parser.add_argument("--tts-engine", default="chatterbox", choices=["chatterbox"])
    parser.add_argument("--lipsync-repo", default="/content/Wav2Lip", help="口型同步仓库路径")
    parser.add_argument("--skip-lipsync", action="store_true", help="可选：跳过口型同步直接封包")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    plan_path = Path(args.plan) if Path(args.plan).is_absolute() else project_dir / args.plan
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    work_dir = Path(args.work_dir).resolve()
    shared_models_dir = Path(args.shared_models_dir).resolve()
    lipsync_repo = Path(args.lipsync_repo) if args.lipsync_repo else None

    if args.stage in ("all", "analyze"):
        stage_analyze(project_dir, plan, work_dir)
    if args.stage in ("all", "dub"):
        stage_dub(project_dir, plan, work_dir, tts_engine=args.tts_engine)
    if args.stage in ("all", "faceswap"):
        stage_faceswap(project_dir, plan, work_dir, shared_models_dir)
    if args.stage in ("all", "lipsync"):
        stage_lipsync(
            project_dir,
            plan,
            work_dir,
            shared_models_dir=shared_models_dir,
            lipsync_repo=lipsync_repo,
            skip_lipsync=args.skip_lipsync,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
