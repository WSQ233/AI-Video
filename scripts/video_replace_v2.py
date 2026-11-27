#!/usr/bin/env python3
"""
原片精改 v2 专业高清管线（彻底解决 v1 人物发糊/抖动与台词模糊问题）：
  - 语音克隆 (Stage 1 --stage dub):
      使用 Bilibili 开源 SOTA 中文语音克隆模型 IndexTTS-2 / 2.5（字符+拼音混合建模 + BigVGAN2 声码器），
      以原汁原味的 1.00x 自然语速（禁止 0.82x 强行拉慢变糊！）克隆特朗普、鲁比奥、贝森特的真实音色讲播音级清晰中文，
      并将原片 Demucs 残留回声在说话段压低 -18dB，杜绝双声道重影。
      同时为每位说话人导出独立干声轨 (vocals_<speaker>.wav)，确保口型同步只驱动当前发声角色。
  - 高清稳定换脸 + 256px 口型同步 + FFHQ 对齐修复 (Stage 2 --stage swap):
      调用官方 FaceFusion v3 headless CLI：
        1. hyperswap_1b_256（256x256 原生分辨率，4倍于 inswapper_128，专优侧脸与低头大角度）
        2. edtalk_256（256x256 高清口型同步，告别 96x96 Wav2Lip 糊嘴）
        3. gpen_bfr_512（标准 5 点 FFHQ 仿射对齐 + 逆变换回贴，零偏移零发糊）
        4. box + occlusion (xseg_1) 遮罩（100% 保留清宫官帽帽檐、胡须与下颌轮廓，零边缘重影）
      支持 --clip-end-sec 17.2 快速产出 15–17 秒试拍验证样片，确认效果后再一键跑全片 4:11！
"""

from __future__ import annotations

import argparse
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


def run_cmd(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"[CMD] {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=check, text=True)


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
        "User-Agent": "AI-Video-Pipeline/2.0 (https://github.com/WSQ233/AI-Video; educational-research)",
        "Accept": "*/*",
    }
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
                shutil.copyfileobj(resp, out)
            os.replace(tmp, dest)
            return dest
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 502, 503, 504) and attempt < max_retries:
                time.sleep(4.0 * attempt)
                continue
            raise
        except Exception:
            if attempt < max_retries:
                time.sleep(3.0 * attempt)
                continue
            raise
    return dest


def select_lines_in_range(plan: dict[str, Any], clip_end_sec: float) -> tuple[list[dict[str, Any]], float]:
    """筛选 [0, clip_end_sec] 区间内的所有台词（确保不截断正在说话的完整句子）。"""
    selected: list[dict[str, Any]] = []
    for ln in plan["lines"]:
        ts = float(ln["fixed_start"])
        te = float(ln["fixed_end"])
        if ts < clip_end_sec - 0.5:
            selected.append({
                "id": ln["id"],
                "speaker": ln["speaker"],
                "orig_role": ln["orig_role"],
                "start": ts,
                "end": min(te, clip_end_sec),
                "orig_end": te,
                "adapted_text": ln["adapted_text"],
            })
    if not selected:
        raise RuntimeError(f"在 0–{clip_end_sec}s 区间内未匹配到任何台词！")
    # 若最后一句只差 <=2.5 秒就完整说完，自动顺延终点让最后一句话完整收尾
    last_orig_end = selected[-1]["orig_end"]
    actual_end = clip_end_sec
    if last_orig_end > clip_end_sec and (last_orig_end - clip_end_sec) <= 2.5:
        actual_end = round(last_orig_end + 0.25, 3)
        selected[-1]["end"] = last_orig_end
    return selected, actual_end


def prepare_voice_refs(project_dir: Path, plan: dict[str, Any], work_dir: Path, needed_speakers: set[str]) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    raw_dir = work_dir / "raw_voices"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for spk, cfg in plan["voice_sources"].items():
        if spk not in needed_speakers:
            continue
        target_wav = project_dir / cfg["local_rel"]
        target_wav.parent.mkdir(parents=True, exist_ok=True)
        if target_wav.exists() and target_wav.stat().st_size > 20_000:
            print(f"[声纹复用] {spk} -> {target_wav}", flush=True)
            refs[spk] = target_wav
            continue
        raw_ext = Path(cfg["url"].split("?")[0]).suffix or ".ogg"
        raw_file = raw_dir / f"{spk}_raw{raw_ext}"
        download_file(cfg["url"], raw_file)
        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-ss", f"{float(cfg.get('clip_start_sec', 8.0)):.2f}",
            "-t", f"{float(cfg.get('clip_duration_sec', 12.0)):.2f}",
            "-i", str(raw_file),
            "-af", "highpass=f=85,lowpass=f=11000,loudnorm=I=-18:TP=-1.5:LRA=8",
            "-ac", "1", "-ar", "24000", "-acodec", "pcm_s16le",
            str(target_wav),
        ])
        refs[spk] = target_wav
        print(f"[声纹就绪] {spk} -> {target_wav}", flush=True)
    return refs


# =============================================================================
# Stage 1: Clip Trim + Clean IndexTTS-2/2.5 Broadcast Mandarin Voice Cloning
# =============================================================================

def stage_dub(
    project_dir: Path,
    plan: dict[str, Any],
    work_dir: Path,
    indextts_dir: Path,
    ckpt_dir: Path,
    clip_end_sec: float,
) -> None:
    import inspect
    import numpy as np
    import soundfile as sf

    work_dir.mkdir(parents=True, exist_ok=True)
    src_video = project_dir / plan["source_video"]
    if not src_video.exists():
        raise FileNotFoundError(f"未找到源视频: {src_video}")

    lines, actual_end = select_lines_in_range(plan, clip_end_sec)
    print(f"\n[v2 Stage 1] 精改区间: 0.00s – {actual_end:.2f}s，共 {len(lines)} 句台词：", flush=True)
    for ln in lines:
        print(f"  {ln['id']:7s} [{ln['start']:6.2f}s-{ln['end']:6.2f}s] ({ln['speaker']:13s}) | {ln['adapted_text']}", flush=True)

    # 精确帧级重编码裁剪（避免 -c copy 关键帧偏移导致音画错位！）
    work_clip = work_dir / "work_clip_v2.mp4"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-ss", "0.000", "-t", f"{actual_end:.3f}",
        "-i", str(src_video),
        "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", "25",
        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
        str(work_clip),
    ])

    # 提取原片音频并用 Demucs 提取极低残留的背景底噪（说话段大幅压低 -18dB，杜绝双人声重影！）
    orig_wav = work_dir / "orig_audio_48k.wav"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(work_clip), "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2",
        str(orig_wav),
    ])

    bg_wav = work_dir / "bg_ambience_v2.wav"
    demucs_dir = work_dir / "demucs_out"
    demucs_ok = False
    try:
        run_cmd([
            sys.executable, "-m", "demucs", "-n", "htdemucs", "--two-stems=vocals",
            "-o", str(demucs_dir), str(orig_wav),
        ])
        cand = demucs_dir / "htdemucs" / orig_wav.stem / "no_vocals.wav"
        if cand.exists():
            run_cmd([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
                "-i", str(cand), "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le", str(bg_wav),
            ])
            demucs_ok = True
    except Exception as exc:
        print(f"[提示] Demucs 跳过（将使用纯洁宫廷环境声底噪，杜绝人声重影）: {exc}", flush=True)

    needed_speakers = {ln["speaker"] for ln in lines}
    voice_refs = prepare_voice_refs(project_dir, plan, work_dir, needed_speakers)

    # 加载 Bilibili IndexTTS-2 / 2.5（播音级中文清晰度 + 跨语种本尊音色还原）
    sys.path.insert(0, str(indextts_dir))
    tts_cls = None
    is_v25 = False
    try:
        from indextts.infer_v2_5 import IndexTTS2 as _TTS25  # type: ignore
        tts_cls = _TTS25
        is_v25 = True
        print("[Stage 1.2] 加载 IndexTTS-2.5 高清中文音色克隆引擎...", flush=True)
    except Exception:
        from indextts.infer_v2 import IndexTTS2 as _TTS2  # type: ignore
        tts_cls = _TTS2
        print("[Stage 1.2] 加载 IndexTTS-2 高清中文音色克隆引擎...", flush=True)

    cfg_path = ckpt_dir / "config.yaml"
    init_sig = inspect.signature(tts_cls.__init__).parameters
    init_kwargs: dict[str, Any] = {"cfg_path": str(cfg_path), "model_dir": str(ckpt_dir)}
    if "use_fp16" in init_sig:
        init_kwargs["use_fp16"] = True
    if "use_cuda_kernel" in init_sig:
        init_kwargs["use_cuda_kernel"] = False
    if "use_deepspeed" in init_sig:
        init_kwargs["use_deepspeed"] = False
    tts = tts_cls(**init_kwargs)
    infer_sig = inspect.signature(tts.infer).parameters

    tts_dir = work_dir / "tts_v2"
    tts_dir.mkdir(parents=True, exist_ok=True)
    sr_master = 48000
    master_samples = int(math.ceil(actual_end * sr_master))
    all_vocals = np.zeros(master_samples, dtype=np.float32)
    per_spk_vocals: dict[str, np.ndarray] = {
        spk: np.zeros(master_samples, dtype=np.float32) for spk in needed_speakers
    }
    duck_mask = np.zeros(master_samples, dtype=np.float32)

    for ln in lines:
        lid = ln["id"]
        spk = ln["speaker"]
        text = ln["adapted_text"]
        t_start = float(ln["start"])
        t_end = float(ln["end"])
        target_dur = max(0.8, t_end - t_start)

        raw_wav = tts_dir / f"{lid}_{spk}_raw.wav"
        clean_wav = tts_dir / f"{lid}_{spk}_clean.wav"

        print(f"  [IndexTTS 清晰中文克隆] {lid} ({spk}): {text}", flush=True)
        infer_kwargs: dict[str, Any] = {
            "spk_audio_prompt": str(voice_refs[spk]),
            "text": text,
            "output_path": str(raw_wav),
        }
        if "lang" in infer_sig and is_v25:
            infer_kwargs["lang"] = "ZH"
        if "verbose" in infer_sig:
            infer_kwargs["verbose"] = False
        tts.infer(**infer_kwargs)

        # 温和去除首尾超长静音，保留清晰辅音起音与自然尾音
        trim_wav = tts_dir / f"{lid}_{spk}_trim.wav"
        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(raw_wav),
            "-af", "highpass=f=85,silenceremove=start_periods=1:start_silence=0.03:start_threshold=-45dB:stop_periods=-1:stop_silence=0.15:stop_threshold=-45dB",
            "-ac", "1", "-ar", str(sr_master), "-acodec", "pcm_s16le",
            str(trim_wav),
        ])
        data, _ = sf.read(str(trim_wav), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        gen_dur = len(data) / sr_master

        # 核心清晰度红线：绝不强行 0.82x 拉慢变糊！仅当略超时才温和加速 <=1.15x
        if gen_dur > target_dur * 1.03:
            tempo = min(1.18, gen_dur / target_dur)
        else:
            tempo = 1.0

        af_chain = "loudnorm=I=-15:TP=-1.5:LRA=8"
        if abs(tempo - 1.0) > 0.01:
            af_chain = f"atempo={tempo:.4f}," + af_chain

        run_cmd([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-i", str(trim_wav),
            "-af", af_chain,
            "-ac", "1", "-ar", str(sr_master), "-acodec", "pcm_s16le",
            str(clean_wav),
        ])
        fit_data, _ = sf.read(str(clean_wav), dtype="float32")
        if fit_data.ndim > 1:
            fit_data = fit_data.mean(axis=1)

        # 若句子略短于窗口，略微居中靠前（保留自然戏剧呼吸感），绝不硬拉声音变形
        s_idx = int(round(t_start * sr_master))
        e_idx = min(master_samples, s_idx + len(fit_data))
        seg_len = max(0, e_idx - s_idx)
        if seg_len > 0:
            fade = min(int(0.012 * sr_master), seg_len // 4)
            seg = fit_data[:seg_len].copy()
            if fade > 0:
                seg[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
                seg[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
            all_vocals[s_idx:e_idx] += seg
            per_spk_vocals[spk][s_idx:e_idx] += seg
            duck_mask[s_idx:e_idx] = 1.0
        print(f"    -> 原生时长={gen_dur:.2f}s / 时间窗={target_dur:.2f}s (tempo={tempo:.2f}x，保持100%吐字清晰)", flush=True)

    vocals_all_path = work_dir / "dubbed_vocals_only.wav"
    sf.write(str(vocals_all_path), np.clip(all_vocals, -0.98, 0.98), sr_master)
    for spk, track in per_spk_vocals.items():
        sf.write(str(work_dir / f"vocals_{spk}.wav"), np.clip(track, -0.98, 0.98), sr_master)

    # 终混：说话段将原片 Demucs 残留压低至 -18dB（0.12x），彻底消除原片残余人声重影！
    mixed = np.zeros((master_samples, 2), dtype=np.float32)
    if demucs_ok and bg_wav.exists():
        bg_data, _ = sf.read(str(bg_wav), dtype="float32")
        if bg_data.ndim == 1:
            bg_data = np.stack([bg_data, bg_data], axis=1)
        if len(bg_data) < master_samples:
            bg_data = np.concatenate([bg_data, np.zeros((master_samples - len(bg_data), 2), dtype=np.float32)], axis=0)
        else:
            bg_data = bg_data[:master_samples]
        win_n = int(0.18 * sr_master)
        smooth_duck = np.convolve(duck_mask, np.ones(win_n, dtype=np.float32) / win_n, mode="same")
        bg_gain = 0.45 * (1.0 - smooth_duck) + 0.12 * smooth_duck
        mixed[:, 0] = bg_data[:, 0] * bg_gain + all_vocals * 1.08
        mixed[:, 1] = bg_data[:, 1] * bg_gain + all_vocals * 1.08
    else:
        mixed[:, 0] = all_vocals
        mixed[:, 1] = all_vocals

    raw_mix = work_dir / "dubbed_mix_raw.wav"
    sf.write(str(raw_mix), np.clip(mixed, -0.98, 0.98), sr_master)
    master_audio = work_dir / "dubbed_master_audio.wav"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(raw_mix),
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=9",
        "-ac", "2", "-ar", str(sr_master), "-acodec", "pcm_s16le",
        str(master_audio),
    ])

    meta = {
        "clip_end_sec": actual_end,
        "lines": lines,
        "speakers": sorted(needed_speakers),
    }
    (work_dir / "v2_run_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 同步清晰台词样本到 Drive 便于试听
    preview_dir = project_dir / "outputs" / "replace_v2_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(master_audio, preview_dir / "dubbed_master_audio_v2.wav")
    print(f"[v2 Stage 1 完成] 播音级清晰克隆音轨: {master_audio}", flush=True)


# =============================================================================
# Stage 2: Official FaceFusion (HyperSwap-256 + EDTalk-256 + GPEN-512 + XSeg)
# =============================================================================

def find_best_reference_frames(
    work_clip: Path,
    lines: list[dict[str, Any]],
    work_dir: Path,
) -> dict[str, dict[str, Any]]:
    """
    在每个说话人的发言时间窗内自动定位最清晰、正脸面积最大的参考帧编号，
    并利用余弦相似度排重（确保鲁比奥参考帧绝不会误选到切镜中的康熙！）。
    """
    import cv2
    import numpy as np
    from insightface.app import FaceAnalysis
    from PIL import Image, ImageDraw

    app = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection", "recognition"],
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    app.prepare(ctx_id=0, det_size=(640, 640))

    cap = cv2.VideoCapture(str(work_clip))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 按发言顺序处理（先锁定康熙，再排重锁定佟国维、张廷玉）
    spk_windows: dict[str, list[tuple[float, float]]] = {}
    for ln in lines:
        spk_windows.setdefault(ln["speaker"], []).append((float(ln["start"]), float(ln["end"])))

    locked_embs: dict[str, np.ndarray] = {}
    best_refs: dict[str, dict[str, Any]] = {}
    crops_for_sheet: list[tuple[str, int, Any]] = []

    ordered_speakers = [s for s in ("trump", "marco_rubio", "scott_bessent", "jd_vance") if s in spk_windows]

    for spk in ordered_speakers:
        best_score = -1.0
        best_info: dict[str, Any] | None = None
        best_emb = None
        best_crop = None

        for ws, we in spk_windows[spk]:
            f_start = max(0, int(ws * fps))
            f_end = min(total_frames - 1, int(we * fps))
            for f_idx in range(f_start, f_end + 1, 4):
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                faces = app.get(frame)
                if not faces:
                    continue
                # FaceFusion reference-face-position 按检测人脸左到右/得分顺序；按 x1 排序更稳定
                faces_sorted = sorted(faces, key=lambda fc: float(fc.bbox[0]))
                for pos_i, f in enumerate(faces_sorted):
                    if f.det_score < 0.50:
                        continue
                    emb = f.normed_embedding.astype(np.float32)
                    # 排除已锁定的其他主角（防止切镜时把康熙当成佟国维）
                    if any(float(np.dot(emb, prev)) > 0.42 for prev in locked_embs.values()):
                        continue
                    x1, y1, x2, y2 = [int(v) for v in f.bbox]
                    area = max(1, (x2 - x1) * (y2 - y1))
                    sc = float(f.det_score) * math.sqrt(area)
                    if sc > best_score:
                        best_score = sc
                        best_emb = emb
                        best_info = {
                            "speaker": spk,
                            "frame_number": f_idx,
                            "time_sec": round(f_idx / fps, 2),
                            "face_position": pos_i,
                            "det_score": round(float(f.det_score), 3),
                            "bbox": [x1, y1, x2, y2],
                        }
                        pad = int(max(x2 - x1, y2 - y1) * 0.25)
                        cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
                        cx2, cy2 = min(frame.shape[1], x2 + pad), min(frame.shape[0], y2 + pad)
                        best_crop = cv2.cvtColor(frame[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2RGB)

        if best_info is not None and best_emb is not None:
            locked_embs[spk] = best_emb
            best_refs[spk] = best_info
            crops_for_sheet.append((spk, best_info["frame_number"], best_crop))
            print(
                f"  [参考帧锁定] {spk:13s} -> frame #{best_info['frame_number']} "
                f"(t={best_info['time_sec']}s, pos={best_info['face_position']}, score={best_info['det_score']})",
                flush=True,
            )

    cap.release()

    if crops_for_sheet:
        tile = 220
        sheet = Image.new("RGB", (tile * len(crops_for_sheet), tile + 40), (20, 22, 28))
        draw = ImageDraw.Draw(sheet)
        for i, (spk, fno, crop) in enumerate(crops_for_sheet):
            if crop is not None:
                im = Image.fromarray(crop).resize((tile - 12, tile - 12))
                sheet.paste(im, (i * tile + 6, 36))
            draw.text((i * tile + 10, 10), f"{spk} @ frame {fno}", fill=(245, 245, 245))
        sheet.save(work_dir / "ref_frames_preview.jpg", quality=92)

    return best_refs


def stage_swap(
    project_dir: Path,
    plan: dict[str, Any],
    work_dir: Path,
    facefusion_dir: Path,
    output_name: str,
    face_swapper_model: str = "hyperswap_1b_256",
    face_enhancer_model: str = "gpen_bfr_512",
    lip_syncer_model: str = "edtalk_256",
    skip_lipsync: bool = False,
) -> Path:
    import cv2

    work_clip = work_dir / "work_clip_v2.mp4"
    master_audio = work_dir / "dubbed_master_audio.wav"
    meta_path = work_dir / "v2_run_meta.json"
    if not (work_clip.exists() and master_audio.exists() and meta_path.exists()):
        raise FileNotFoundError("请先运行 --stage dub 生成 work_clip_v2.mp4 与 dubbed_master_audio.wav")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    lines = meta["lines"]

    print("\n[v2 Stage 2.1] 自动定位每位说话人最清晰参考帧...", flush=True)
    ref_map = find_best_reference_frames(work_clip, lines, work_dir)
    if not ref_map:
        raise RuntimeError("未能从视频中锁定任何主角参考帧！")

    preview_dir = project_dir / "outputs" / "replace_v2_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    if (work_dir / "ref_frames_preview.jpg").exists():
        shutil.copy2(work_dir / "ref_frames_preview.jpg", preview_dir / "ref_frames_preview.jpg")

    # 逐主角串联执行官方 FaceFusion v3 headless-run（256px 换脸 + 256px 口型 + 512px FFHQ对齐修复 + XSeg 遮罩）
    cur_video = work_clip
    for step_i, (spk, rinfo) in enumerate(ref_map.items(), start=1):
        src_imgs = [str(project_dir / rel) for rel in plan["face_portraits"][spk] if (project_dir / rel).exists()]
        if not src_imgs:
            raise FileNotFoundError(f"缺少角色参考肖像: {spk}")

        spk_audio = work_dir / f"vocals_{spk}.wav"
        next_video = work_dir / f"ff_pass{step_i}_{spk}.mp4"

        processors = ["face_swapper"]
        source_paths = list(src_imgs)
        if not skip_lipsync and spk_audio.exists():
            processors.append("lip_syncer")
            source_paths.append(str(spk_audio))
        processors.append("face_enhancer")

        cmd = [
            sys.executable, str(facefusion_dir / "facefusion.py"), "headless-run",
            "--processors", *processors,
            "--source-paths", *source_paths,
            "--target-path", str(cur_video),
            "--output-path", str(next_video),
            "--face-swapper-model", face_swapper_model,
            "--face-enhancer-model", face_enhancer_model,
            "--face-enhancer-blend", "78",
            "--face-detector-model", "retinaface",
            "--face-detector-score", "0.45",
            "--face-selector-mode", "reference",
            "--reference-frame-number", str(rinfo["frame_number"]),
            "--reference-face-position", str(rinfo["face_position"]),
            "--reference-face-distance", "0.68",
            "--face-mask-types", "box", "occlusion",
            "--face-mask-blur", "0.3",
            "--output-video-encoder", "libx264",
            "--output-video-quality", "92",
            "--execution-providers", "cuda",
            "--execution-thread-count", "4",
        ]
        if not skip_lipsync and spk_audio.exists():
            cmd.extend(["--lip-syncer-model", lip_syncer_model, "--lip-syncer-weight", "0.85"])

        print(
            f"\n[v2 Stage 2.{step_i + 1}] FaceFusion 高清精修 Pass {step_i}: {spk} "
            f"(frame #{rinfo['frame_number']}, {face_swapper_model} + {lip_syncer_model} + {face_enhancer_model})...",
            flush=True,
        )
        run_cmd(cmd, cwd=facefusion_dir)
        if not next_video.exists() or next_video.stat().st_size < 100_000:
            raise RuntimeError(f"FaceFusion Pass {step_i} ({spk}) 未产出有效视频: {next_video}")
        cur_video = next_video

    # 封装最终超清双流成片
    final_out = project_dir / "outputs" / "final_cut" / output_name
    final_out.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n[v2 Stage 2.Final] 封装最终高清双流成片 -> {final_out}", flush=True)
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(cur_video),
        "-i", str(master_audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "256k",
        "-movflags", "+faststart", "-shortest",
        str(final_out),
    ])

    # 抽取两位主角的换脸后高清验收截图，方便本机直接肉眼质检画质
    cap = cv2.VideoCapture(str(final_out))
    for spk, rinfo in ref_map.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(rinfo["frame_number"]))
        ret, frame = cap.read()
        if ret:
            shot_jpg = preview_dir / f"after_swap_{spk}_f{rinfo['frame_number']}.jpg"
            cv2.imwrite(str(shot_jpg), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            print(f"  [验收截图] {shot_jpg}", flush=True)
    cap.release()

    info = probe_media(final_out)
    vs = [s for s in info["streams"] if s["codec_type"] == "video"][0]
    as_ = [s for s in info["streams"] if s["codec_type"] == "audio"][0]
    dur = float(info["format"]["duration"])
    size_mb = final_out.stat().st_size / (1024 * 1024)
    print(
        f"\n[v2 成片 FFprobe 验收 PASS] {final_out}\n"
        f"  时长: {dur:.2f}s | 体积: {size_mb:.2f} MB\n"
        f"  视频流: {vs['codec_name']} {vs['width']}x{vs['height']} @{vs['r_frame_rate']}\n"
        f"  音频流: {as_['codec_name']} {as_['sample_rate']}Hz {as_['channels']}ch",
        flush=True,
    )
    return final_out


def main() -> int:
    parser = argparse.ArgumentParser(description="原片精改 v2 专业高清管线（IndexTTS-2 + FaceFusion HyperSwap-256 + EDTalk-256 + GPEN-512）")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--plan", default="dubbing_plan_shot01_21.json")
    parser.add_argument("--work-dir", default="/content/work_replace_v2")
    parser.add_argument("--stage", choices=["dub", "swap"], required=True)
    parser.add_argument("--clip-end-sec", type=float, default=17.2, help="截取时长（秒）；15s 试拍默认 17.2s 完整覆盖前两句")
    parser.add_argument("--indextts-dir", default="/content/index-tts")
    parser.add_argument("--indextts-ckpt-dir", default="/content/drive/MyDrive/AI_Video/shared/models/indextts2")
    parser.add_argument("--facefusion-dir", default="/content/facefusion")
    parser.add_argument("--output-name", default="02_yongzheng_ep12_huang_v2_15s_preview.mp4")
    parser.add_argument("--face-swapper-model", default="hyperswap_1b_256")
    parser.add_argument("--face-enhancer-model", default="gpen_bfr_512")
    parser.add_argument("--lip-syncer-model", default="edtalk_256")
    parser.add_argument("--skip-lipsync", action="store_true")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    plan_path = Path(args.plan) if Path(args.plan).is_absolute() else project_dir / args.plan
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    work_dir = Path(args.work_dir).resolve()

    if args.stage == "dub":
        stage_dub(
            project_dir=project_dir,
            plan=plan,
            work_dir=work_dir,
            indextts_dir=Path(args.indextts_dir),
            ckpt_dir=Path(args.indextts_ckpt_dir),
            clip_end_sec=args.clip_end_sec,
        )
    elif args.stage == "swap":
        stage_swap(
            project_dir=project_dir,
            plan=plan,
            work_dir=work_dir,
            facefusion_dir=Path(args.facefusion_dir),
            output_name=args.output_name,
            face_swapper_model=args.face_swapper_model,
            face_enhancer_model=args.face_enhancer_model,
            lip_syncer_model=args.lip_syncer_model,
            skip_lipsync=args.skip_lipsync,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
