#!/usr/bin/env python3
"""
原片语气复刻 + 纯音色替换（15秒 MiniMax H3 样片专属精修脚本）：
1. 对原片前 17s 执行 Demucs (htdemucs --two-stems=vocals) 分离：
   - orig_vocals.wav：100% 保留焦晃/佟国维原汁原味的帝王威严、顿挫气口与戏腔语气
   - orig_bgm.wav：100% 保留原片清宫紧张弦乐伴奏与环境底噪
2. 用 faster-whisper 提取原片人声字级时间戳，定位需要替换的专有名词区间：
   - 康熙句：「为什么没有 [二阿哥胤礽 -> 黄仁勋] 的荐章啊」
   - 佟国维句：「[皇上 -> 总统] 这话奴才不明白，因为废 [二阿哥 -> 黄仁勋]，所以才推荐 [新太子 -> 新CEO]，怎么还会有推举 [二阿哥 -> 黄仁勋] 的荐章」
3. 用 IndexTTS-2 以「原片老戏骨本尊干声」为 spk_audio_prompt + 同句干声为 emo_audio_prompt，
   仅对替换词做语流无缝补丁，先拼出「100% 原片老戏骨语气 + 新台词」的干声母带。
4. 用 Seed-VC (Zero-Shot Speech-to-Speech Voice Conversion) 将整句干声母带纯音色转换为
   特朗普 (ref_trump.wav) 与鲁比奥 (ref_marco_rubio.wav) 真声：
   - 完整锁死原片老戏骨的每一个停顿、重音与音调起伏（语气参考原片）
   - 仅替换声带音色（只是声音替换），同时自然融化补丁接缝。
5. 将原片清宫配乐 (orig_bgm.wav) 混入，精准对齐已通过的 MiniMax H3 4 镜画面口型窗，
   输出无字幕终版 MP4（视频流零降质复用已有 H3 渲染结果）并自动落盘至 5TB Google Drive。
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


SR = 32000


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("[CMD]", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=str(cwd) if cwd else None, check=check, text=True)


def load_mono(path: Path, sr: int = SR) -> np.ndarray:
    tmp = path.with_suffix(".tmp32k.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-acodec", "pcm_s16le", str(tmp)],
        check=True,
    )
    data, _ = sf.read(str(tmp), dtype="float32")
    tmp.unlink(missing_ok=True)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data.astype(np.float32)


def save_wav(path: Path, data: np.ndarray, sr: int = SR) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(data, -0.98, 0.98), sr, subtype="PCM_16")
    return path


def rms_db(arr: np.ndarray) -> float:
    if len(arr) == 0:
        return -90.0
    val = float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
    return 20.0 * math.log10(max(val, 1e-6))


def crossfade_concat(parts: list[np.ndarray], xfade_sec: float = 0.025, sr: int = SR) -> np.ndarray:
    parts = [p for p in parts if len(p) > 0]
    if not parts:
        return np.zeros(0, dtype=np.float32)
    out = parts[0].copy()
    xf = int(round(xfade_sec * sr))
    for nxt in parts[1:]:
        n = min(xf, len(out) // 3, len(nxt) // 3)
        if n <= 1:
            out = np.concatenate([out, nxt])
        else:
            w_out = np.linspace(1.0, 0.0, n, dtype=np.float32)
            w_in = np.linspace(0.0, 1.0, n, dtype=np.float32)
            blend = out[-n:] * w_out + nxt[:n] * w_in
            out = np.concatenate([out[:-n], blend, nxt[n:]])
    return out


def time_stretch(arr: np.ndarray, target_dur: float, min_rate: float = 0.88, max_rate: float = 1.18, sr: int = SR) -> np.ndarray:
    cur_dur = len(arr) / sr
    if cur_dur <= 0.05 or target_dur <= 0.05:
        return arr
    rate = cur_dur / target_dur
    if 0.96 <= rate <= 1.04:
        return arr
    rate = max(min_rate, min(max_rate, rate))
    tmp_in = Path("/tmp/_ts_in.wav")
    tmp_out = Path("/tmp/_ts_out.wav")
    save_wav(tmp_in, arr, sr)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(tmp_in),
            "-af", f"atempo={rate:.4f}",
            "-ac", "1", "-ar", str(sr), "-acodec", "pcm_s16le",
            str(tmp_out),
        ],
        check=True,
    )
    res, _ = sf.read(str(tmp_out), dtype="float32")
    tmp_in.unlink(missing_ok=True)
    tmp_out.unlink(missing_ok=True)
    return res.astype(np.float32)


def trim_silence(arr: np.ndarray, thresh_db: float = -40.0, pad_sec: float = 0.03, sr: int = SR) -> np.ndarray:
    win = int(0.02 * sr)
    if len(arr) <= win:
        return arr
    thresh = 10.0 ** (thresh_db / 20.0)
    active = []
    for i in range(0, len(arr) - win, win // 2):
        seg = arr[i:i + win]
        if float(np.sqrt(np.mean(seg ** 2))) > thresh:
            active.append(i)
    if not active:
        return arr
    pad = int(pad_sec * sr)
    s = max(0, active[0] - pad)
    e = min(len(arr), active[-1] + win + pad)
    return arr[s:e].copy()


def transcribe_chars(whisper_model: Any, wav_path: Path, initial_prompt: str = "") -> list[dict[str, Any]]:
    # 直接传入 16kHz float32 numpy 数组，彻底绕开新版 PyAV 与 faster-whisper decode_audio 的 metadata_errors 兼容问题
    audio_16k = load_mono(wav_path, sr=16000)
    segments, _ = whisper_model.transcribe(
        audio_16k,
        language="zh",
        word_timestamps=True,
        vad_filter=False,
        initial_prompt=initial_prompt,
    )
    chars: list[dict[str, Any]] = []
    for seg in segments:
        for w in (seg.words or []):
            token = w.word.strip()
            if not token:
                continue
            # 将多字词均匀拆成字级区间，方便精确匹配替换子串
            clean_chars = [c for c in token if not c.isspace()]
            if not clean_chars:
                continue
            dt = max(0.02, float(w.end) - float(w.start)) / len(clean_chars)
            for idx, ch in enumerate(clean_chars):
                chars.append({
                    "ch": ch,
                    "start": float(w.start) + idx * dt,
                    "end": float(w.start) + (idx + 1) * dt,
                })
    return chars


def find_span(chars: list[dict[str, Any]], targets: list[str], search_from: float = 0.0, search_to: float = 999.0) -> tuple[float, float] | None:
    sub = [c for c in chars if c["start"] >= search_from - 0.15 and c["end"] <= search_to + 0.15]
    text = "".join(c["ch"] for c in sub)
    for tgt in targets:
        pos = text.find(tgt)
        if pos != -1:
            return sub[pos]["start"], sub[pos + len(tgt) - 1]["end"]
    return None


def find_shot_output(batch_dir: Path, task_id: str) -> Path:
    cands = sorted(batch_dir.glob(f"{task_id}*.mp4"))
    if not cands:
        raise FileNotFoundError(f"找不到 MiniMax H3 分镜输出: {batch_dir}/{task_id}*.mp4")
    return cands[-1]


def ensure_deps(seed_vc_dir: Path, indextts_dir: Path) -> None:
    # 1. 基础音频与对齐工具
    for pkg, mod in [
        ("demucs", "demucs"),
        ("faster-whisper", "faster_whisper"),
        ("soundfile", "soundfile"),
        ("librosa", "librosa"),
        ("munch", "munch"),
        ("einops", "einops"),
        ("hf_xet", "hf_xet"),
    ]:
        try:
            __import__(mod)
        except Exception:
            run_cmd([sys.executable, "-m", "pip", "install", "-q", pkg])

    # 2. Seed-VC 仓库（零样本 Speech-to-Speech 音色转换，100% 保留源语音语气与停顿）
    if not (seed_vc_dir / "inference.py").is_file():
        if seed_vc_dir.exists():
            shutil.rmtree(seed_vc_dir)
        run_cmd(["git", "clone", "--depth", "1", "https://github.com/Plachtaa/seed-vc.git", str(seed_vc_dir)])
    # 安装 Seed-VC 所需轻量依赖（避免覆盖 torch）
    for pkg in ("pyyaml", "scipy", "torchaudio", "transformers", "huggingface_hub", "hydra-core", "omegaconf", "protobuf>=5.29.1"):
        try:
            if pkg.startswith("protobuf"):
                run_cmd([sys.executable, "-m", "pip", "install", "-q", pkg], check=False)
            else:
                __import__(pkg.replace("-", "_").split("_")[0])
        except Exception:
            run_cmd([sys.executable, "-m", "pip", "install", "-q", pkg])

    # 3. IndexTTS-2 仓库（仅用于生成少量替换名词并用原片演员音色+情感补丁）
    if not (indextts_dir / "indextts" / "infer_v2.py").is_file():
        if indextts_dir.exists():
            shutil.rmtree(indextts_dir)
        run_cmd(["git", "clone", "--depth", "1", "https://github.com/index-tts/index-tts.git", str(indextts_dir)])
        for pkg in ("cn2an", "g2p-en", "jieba", "pypinyin", "WeTextProcessing", "sentencepiece", "safetensors", "accelerate"):
            try:
                run_cmd([sys.executable, "-m", "pip", "install", "-q", pkg], check=False)
            except Exception:
                pass


def ensure_indextts_ckpt(shared_models_dir: Path) -> Path:
    ckpt_dir = shared_models_dir / "indextts2"
    if (ckpt_dir / "config.yaml").is_file() and any(ckpt_dir.glob("*.pth")):
        print(f"[模型复用] IndexTTS-2 权重已存在: {ckpt_dir}", flush=True)
        return ckpt_dir
    from huggingface_hub import snapshot_download
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    print(f"[下载] 拉取 IndexTeam/IndexTTS-2 到 {ckpt_dir}...", flush=True)
    snapshot_download(repo_id="IndexTeam/IndexTTS-2", local_dir=str(ckpt_dir))
    return ckpt_dir


def run_seed_vc(
    seed_vc_dir: Path,
    source_wav: Path,
    target_wav: Path,
    out_dir: Path,
    diffusion_steps: int = 40,
    cfg_rate: float = 0.7,
    semi_tone_shift: int = 0,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    before = set(out_dir.glob("*.wav"))
    run_cmd(
        [
            sys.executable,
            str(seed_vc_dir / "inference.py"),
            "--source", str(source_wav),
            "--target", str(target_wav),
            "--output", str(out_dir),
            "--diffusion-steps", str(diffusion_steps),
            "--length-adjust", "1.0",
            "--inference-cfg-rate", str(cfg_rate),
            "--f0-condition", "False",
            "--semi-tone-shift", str(semi_tone_shift),
            "--fp16", "True",
        ],
        cwd=seed_vc_dir,
    )
    after = sorted(set(out_dir.glob("*.wav")) - before, key=lambda p: p.stat().st_mtime)
    if not after:
        after = sorted(out_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime)
    if not after:
        raise FileNotFoundError(f"Seed-VC 未在 {out_dir} 生成输出 wav")
    return after[-1]


def extract_word_from_phrase(
    tts: Any,
    infer_sig: Any,
    whisper_model: Any,
    spk_prompt: Path,
    emo_prompt: Path,
    phrase: str,
    target_substrings: list[str],
    work_dir: Path,
    tag: str,
) -> np.ndarray:
    raw_wav = work_dir / f"patch_{tag}_full.wav"
    kwargs: dict[str, Any] = {
        "spk_audio_prompt": str(spk_prompt),
        "text": phrase,
        "output_path": str(raw_wav),
    }
    if "emo_audio_prompt" in infer_sig:
        kwargs["emo_audio_prompt"] = str(emo_prompt)
    if "emo_alpha" in infer_sig:
        kwargs["emo_alpha"] = 0.95
    if "verbose" in infer_sig:
        kwargs["verbose"] = False
    tts.infer(**kwargs)

    arr = load_mono(raw_wav, SR)
    chars = transcribe_chars(whisper_model, raw_wav, initial_prompt=phrase)
    print(f"  [补词定位] {tag} ({phrase}) -> {''.join(c['ch'] for c in chars)}", flush=True)
    span = find_span(chars, target_substrings)
    if span is not None:
        s_t = max(0.0, span[0] - 0.03)
        e_t = min(len(arr) / SR, span[1] + 0.04)
        clip = arr[int(s_t * SR):int(e_t * SR)]
        print(f"    -> 截取目标词 {target_substrings[0]}: [{s_t:.2f}s - {e_t:.2f}s] ({len(clip)/SR:.2f}s)", flush=True)
        return clip
    # 兜底：若整句定位失败，直接单独合成目标词
    print(f"    -> [兜底] 整句未匹配到 {target_substrings}，改用短词直出", flush=True)
    solo_wav = work_dir / f"patch_{tag}_solo.wav"
    kwargs["text"] = target_substrings[0]
    kwargs["output_path"] = str(solo_wav)
    tts.infer(**kwargs)
    return trim_silence(load_mono(solo_wav, SR), thresh_db=-42.0, pad_sec=0.025)


def match_rms(src: np.ndarray, ref: np.ndarray, max_gain: float = 2.5) -> np.ndarray:
    r_src = float(np.sqrt(np.mean(src.astype(np.float64) ** 2))) + 1e-6
    r_ref = float(np.sqrt(np.mean(ref.astype(np.float64) ** 2))) + 1e-6
    gain = min(max_gain, max(1.0 / max_gain, r_ref / r_src))
    return (src * gain).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="原片语气复刻 + Seed-VC 音色替换（复用已通过的 MiniMax H3 15s 画面）")
    parser.add_argument("--project-dir", default="/content/drive/MyDrive/AI_Video/projects/02_yongzheng_ep12_huang")
    parser.add_argument("--shared-models-dir", default="/content/drive/MyDrive/AI_Video/shared/models")
    parser.add_argument("--batch-name", default="h3_15s_test_v1")
    parser.add_argument("--work-dir", default="/content/work_origtone_15s")
    parser.add_argument("--seed-vc-dir", default="/content/Seed-VC")
    parser.add_argument("--indextts-dir", default="/content/index-tts")
    parser.add_argument("--diffusion-steps", type=int, default=40)
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    shared_models_dir = Path(args.shared_models_dir)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    seed_vc_dir = Path(args.seed_vc_dir)
    indextts_dir = Path(args.indextts_dir)

    raw_video = project_dir / "videos" / "raw_court_ep12.mp4"
    ref_trump = project_dir / "characters" / "trump" / "voice" / "ref_trump.wav"
    ref_rubio = project_dir / "characters" / "marco_rubio" / "voice" / "ref_marco_rubio.wav"
    for req in (raw_video, ref_trump, ref_rubio):
        if not req.is_file():
            raise FileNotFoundError(f"缺少必要素材: {req}")

    ensure_deps(seed_vc_dir, indextts_dir)
    ckpt_dir = ensure_indextts_ckpt(shared_models_dir)

    # -------------------------------------------------------------------------
    # Stage 1: 提取原片 0-17.5s 音频并用 Demucs 彻底分离「老戏骨干声」与「清宫配乐」
    # -------------------------------------------------------------------------
    orig_17s_wav = work_dir / "orig_17s.wav"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-ss", "0.00", "-t", "17.50", "-i", str(raw_video),
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(orig_17s_wav),
    ])

    demucs_out = work_dir / "demucs"
    run_cmd([
        sys.executable, "-m", "demucs", "-n", "htdemucs", "--two-stems=vocals",
        "-o", str(demucs_out), str(orig_17s_wav),
    ])
    stem_dir = demucs_out / "htdemucs" / orig_17s_wav.stem
    orig_vocals_wav = stem_dir / "vocals.wav"
    orig_bgm_wav = stem_dir / "no_vocals.wav"
    orig_vocals = load_mono(orig_vocals_wav, SR)
    # 同时保存 32kHz 单声道干净原片干声，供 Whisper 和 IndexTTS 使用
    orig_vocals_32k = save_wav(work_dir / "orig_vocals_32k.wav", orig_vocals, SR)

    # 切出康熙与佟国维本尊原声参考（供 IndexTTS-2 生成极少量替换词时保持 100% 老戏骨本尊音色与语气）
    kangxi_ref = save_wav(work_dir / "orig_kangxi_ref.wav", orig_vocals[int(1.45 * SR):int(4.45 * SR)], SR)
    tong_ref = save_wav(work_dir / "orig_tong_ref.wav", orig_vocals[int(5.90 * SR):int(16.60 * SR)], SR)

    # -------------------------------------------------------------------------
    # Stage 2: Whisper 字级对齐原片老戏骨干声
    # -------------------------------------------------------------------------
    from faster_whisper import WhisperModel
    print("[Stage 2] 加载 faster-whisper (medium) 对原片干声执行字级对齐...", flush=True)
    wmodel = WhisperModel("medium", device="cuda", compute_type="float16")
    orig_prompt = "为什么没有二阿哥胤礽的荐章啊？皇上这话奴才不明白，因为废二阿哥，所以才推荐新太子，怎么还会有推举二阿哥的荐章？"
    orig_chars = transcribe_chars(wmodel, orig_vocals_32k, initial_prompt=orig_prompt)
    print("[原片字级识别结果]:", flush=True)
    for c in orig_chars:
        print(f"  {c['start']:5.2f}s-{c['end']:5.2f}s: {c['ch']}", flush=True)

    # 定位 5 处原片分句和待替换专有名词的时间区间
    # Clause 0 (Kangxi): 为什么没有 [二阿哥胤礽] 的荐章啊 (1.50s - 4.45s)
    c0_s, c0_e = 1.55, 4.45
    span_c0_rep = find_span(orig_chars, ["二阿哥胤礽", "二阿哥英人", "二阿哥应仍", "二阿哥"], c0_s, c0_e)
    if span_c0_rep is None:
        span_c0_rep = (2.38, 3.35)
    print(f"[定位 C0 康熙替换词] {span_c0_rep}", flush=True)

    # Clause 1 (Tong): [皇上] 这话奴才不明白 (5.95s - 9.00s)
    c1_s, c1_e = 5.95, 8.95
    span_c1_rep = find_span(orig_chars, ["皇上", "皇"], c1_s, 7.20)
    if span_c1_rep is None:
        span_c1_rep = (6.00, 6.48)
    print(f"[定位 C1 佟国维替换词 皇上] {span_c1_rep}", flush=True)

    # Clause 2 (Tong): 因为废 [二阿哥] (9.45s - 11.45s)
    c2_s, c2_e = 9.45, 11.45
    span_c2_rep = find_span(orig_chars, ["二阿哥", "阿哥"], c2_s, c2_e)
    if span_c2_rep is None:
        span_c2_rep = (10.35, 11.20)
    print(f"[定位 C2 佟国维替换词 二阿哥] {span_c2_rep}", flush=True)

    # Clause 3 (Tong): 所以才推荐 [新太子] (11.50s - 13.75s)
    c3_s, c3_e = 11.50, 13.75
    span_c3_rep = find_span(orig_chars, ["新太子", "太子"], c3_s, c3_e)
    if span_c3_rep is None:
        span_c3_rep = (12.60, 13.55)
    print(f"[定位 C3 佟国维替换词 新太子] {span_c3_rep}", flush=True)

    # Clause 4 (Tong): 怎么还会有推举 [二阿哥] 的荐章 (14.40s - 17.20s)
    c4_s, c4_e = 14.35, 17.20
    span_c4_rep = find_span(orig_chars, ["二阿哥", "阿哥"], c4_s, c4_e)
    if span_c4_rep is None:
        span_c4_rep = (15.65, 16.35)
    # 找到“荐章”结尾防止拖尾进入下一句
    span_c4_end = find_span(orig_chars, ["荐章", "见章", "建章", "章"], 15.80, 17.30)
    if span_c4_end is not None:
        c4_e = min(17.30, span_c4_end[1] + 0.12)
    print(f"[定位 C4 佟国维替换词 二阿哥] {span_c4_rep} | c4_e={c4_e:.2f}s", flush=True)

    # -------------------------------------------------------------------------
    # Stage 3: 用 IndexTTS-2 以原片老戏骨声线+语气生成 5 个替换词，无缝补丁进原片干声
    # -------------------------------------------------------------------------
    sys.path.insert(0, str(indextts_dir))
    from indextts.infer_v2 import IndexTTS2  # type: ignore

    print("[Stage 3] 加载 IndexTTS-2 生成原片同声线/同语气专有名词补丁...", flush=True)
    init_sig = inspect.signature(IndexTTS2.__init__).parameters
    init_kwargs: dict[str, Any] = {"cfg_path": str(ckpt_dir / "config.yaml"), "model_dir": str(ckpt_dir)}
    if "use_fp16" in init_sig:
        init_kwargs["use_fp16"] = True
    if "use_cuda_kernel" in init_sig:
        init_kwargs["use_cuda_kernel"] = False
    if "use_deepspeed" in init_sig:
        init_kwargs["use_deepspeed"] = False
    tts = IndexTTS2(**init_kwargs)
    infer_sig = inspect.signature(tts.infer).parameters

    def sl(t0: float, t1: float) -> np.ndarray:
        a = max(0, int(round(t0 * SR)))
        b = min(len(orig_vocals), int(round(t1 * SR)))
        return orig_vocals[a:b].copy() if b > a else np.zeros(0, dtype=np.float32)

    # 补丁 0: 康熙「黄仁勋」
    p_c0_huang = extract_word_from_phrase(
        tts, infer_sig, wmodel, kangxi_ref, kangxi_ref,
        "为什么没有，黄仁勋的荐章啊？", ["黄仁勋", "仁勋"], work_dir, "c0_huang",
    )
    c0_pre = sl(c0_s, span_c0_rep[0] + 0.02)
    c0_post = sl(max(span_c0_rep[1] - 0.02, span_c0_rep[0] + 0.2), c0_e)
    p_c0_huang = match_rms(p_c0_huang, c0_pre)
    # 略微放慢 0.94x 匹配焦晃慢节奏气口
    p_c0_huang = time_stretch(p_c0_huang, max(0.62, len(p_c0_huang) / SR * 1.06), min_rate=0.88, max_rate=1.08)
    patched_c0 = trim_silence(crossfade_concat([c0_pre, np.zeros(int(0.06 * SR), dtype=np.float32), p_c0_huang, c0_post], 0.022), -42.0, 0.04)

    # 补丁 1: 佟国维「总统」
    c1_emo = save_wav(work_dir / "emo_c1.wav", sl(c1_s, c1_e), SR)
    p_c1_pres = extract_word_from_phrase(
        tts, infer_sig, wmodel, tong_ref, c1_emo,
        "总统这话，奴才不明白。", ["总统"], work_dir, "c1_pres",
    )
    c1_post = sl(span_c1_rep[1] - 0.01, c1_e)
    p_c1_pres = match_rms(p_c1_pres, c1_post)
    patched_c1 = trim_silence(crossfade_concat([p_c1_pres, c1_post], 0.020), -42.0, 0.03)

    # 补丁 2: 佟国维「因为废 [黄仁勋]」
    c2_emo = save_wav(work_dir / "emo_c2.wav", sl(c2_s, c2_e), SR)
    p_c2_huang = extract_word_from_phrase(
        tts, infer_sig, wmodel, tong_ref, c2_emo,
        "因为废黄仁勋，", ["黄仁勋", "仁勋"], work_dir, "c2_huang",
    )
    c2_pre = sl(c2_s, span_c2_rep[0] + 0.01)
    p_c2_huang = match_rms(p_c2_huang, c2_pre)
    patched_c2 = trim_silence(crossfade_concat([c2_pre, p_c2_huang], 0.020), -42.0, 0.03)

    # 补丁 3: 佟国维「所以才推荐 [新CEO]」
    c3_emo = save_wav(work_dir / "emo_c3.wav", sl(c3_s, c3_e), SR)
    p_c3_ceo = extract_word_from_phrase(
        tts, infer_sig, wmodel, tong_ref, c3_emo,
        "所以才推荐新CEO，", ["新CEO", "新ceo", "CEO", "ceo"], work_dir, "c3_ceo",
    )
    c3_pre = sl(c3_s, span_c3_rep[0] + 0.01)
    p_c3_ceo = match_rms(p_c3_ceo, c3_pre)
    patched_c3 = trim_silence(crossfade_concat([c3_pre, p_c3_ceo], 0.020), -42.0, 0.03)

    # 补丁 4: 佟国维「怎么还会有推举 [黄仁勋] 的荐章」
    c4_emo = save_wav(work_dir / "emo_c4.wav", sl(c4_s, c4_e), SR)
    p_c4_huang = extract_word_from_phrase(
        tts, infer_sig, wmodel, tong_ref, c4_emo,
        "怎么还会有推举黄仁勋的荐章？", ["黄仁勋", "仁勋"], work_dir, "c4_huang",
    )
    c4_pre = sl(c4_s, span_c4_rep[0] + 0.01)
    c4_post = sl(span_c4_rep[1] - 0.01, c4_e)
    p_c4_huang = match_rms(p_c4_huang, c4_pre)
    patched_c4 = trim_silence(crossfade_concat([c4_pre, p_c4_huang, c4_post], 0.020), -42.0, 0.04)

    # 释放 IndexTTS-2 与 Whisper 显存，把全部显存留给 Seed-VC
    del tts, wmodel
    import gc, torch
    gc.collect()
    torch.cuda.empty_cache()

    patched_files = {
        "c0_trump": save_wav(work_dir / "patched_c0_kangxi.wav", patched_c0, SR),
        "c1_rubio": save_wav(work_dir / "patched_c1_tong.wav", patched_c1, SR),
        "c2_rubio": save_wav(work_dir / "patched_c2_tong.wav", patched_c2, SR),
        "c3_rubio": save_wav(work_dir / "patched_c3_tong.wav", patched_c3, SR),
        "c4_rubio": save_wav(work_dir / "patched_c4_tong.wav", patched_c4, SR),
    }
    print("[Stage 3 完成] 5 段原片老戏骨语气母带时长:", {k: round(len(load_mono(v, SR)) / SR, 2) for k, v in patched_files.items()}, flush=True)

    # -------------------------------------------------------------------------
    # Stage 4: Seed-VC 纯音色转换（100% 锁死原片老戏骨语气与停顿，仅替换特朗普/鲁比奥声音）
    # -------------------------------------------------------------------------
    print("[Stage 4] 运行 Seed-VC 零样本语音转换（语气100%参考原片，只换音色）...", flush=True)
    vc_out_dir = work_dir / "seed_vc_out"
    vc_clips: dict[str, np.ndarray] = {}
    vc_targets = {
        "c0_trump": ref_trump,
        "c1_rubio": ref_rubio,
        "c2_rubio": ref_rubio,
        "c3_rubio": ref_rubio,
        "c4_rubio": ref_rubio,
    }
    for key, src_wav in patched_files.items():
        sub_out = vc_out_dir / key
        vc_wav = run_seed_vc(
            seed_vc_dir=seed_vc_dir,
            source_wav=src_wav,
            target_wav=vc_targets[key],
            out_dir=sub_out,
            diffusion_steps=args.diffusion_steps,
            cfg_rate=0.7,
            semi_tone_shift=0,
        )
        vc_clips[key] = trim_silence(load_mono(vc_wav, SR), thresh_db=-42.0, pad_sec=0.03)
        print(f"  [Seed-VC OK] {key} -> {vc_wav.name} ({len(vc_clips[key])/SR:.2f}s, {rms_db(vc_clips[key]):.1f}dB)", flush=True)

    # -------------------------------------------------------------------------
    # Stage 5: 复用已通过的 MiniMax H3 4 镜画面，精准对齐 5 句转换后音轨 + 混入原片清宫配乐
    # -------------------------------------------------------------------------
    print("[Stage 5] 复用已验收的 MiniMax H3 4 镜画面，精准对轨并混入原片清宫配乐...", flush=True)
    batch_dir = project_dir / "outputs" / args.batch_name
    s01 = find_shot_output(batch_dir, "h3_15s_s01_trump")
    s02 = find_shot_output(batch_dir, "h3_15s_s02_vance")
    s03a = find_shot_output(batch_dir, "h3_15s_s03a_rubio")
    s03b = find_shot_output(batch_dir, "h3_15s_s03b_rubio")

    # 先按已验证的最佳画面切点与白边裁切拼接纯净视频轨（总时长 12.55s，960x544，24fps，零字幕、零原片演员露脸）
    # 镜头时间段：
    #   [0.00s - 3.75s] s01_trump  (3.75s，口型窗 1.22s - 3.68s)
    #   [3.75s - 4.83s] s02_vance  (1.08s 静默反应镜，1.25s起纯万斯零旧臣残留，原片咚——紧张弦乐切入)
    #   [4.83s - 8.09s] s03a_rubio (3.26s，1.20s起彻底切掉马齐露脸横移，纯鲁比奥；口型窗 C1: 4.92s-6.95s，C2: 7.02s-8.06s)
    #   [8.09s - 12.55s] s03b_rubio (4.46s 满屏特写去白边；口型窗 C3: 8.18s-9.68s，C4: 9.85s-12.48s)
    video_only = work_dir / "h3_15s_video_only.mp4"
    v_fc = (
        "[0:v]fps=24,scale=960:544:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[v0];"
        "[1:v]trim=start=1.250,setpts=PTS-STARTPTS,fps=24,scale=960:544:flags=lanczos,setsar=1[v1];"
        "[2:v]trim=start=1.200,setpts=PTS-STARTPTS,fps=24,scale=960:544:flags=lanczos,setsar=1[v2];"
        "[3:v]crop=572:324:172:28,scale=960:544:flags=lanczos,setsar=1,fps=24,setpts=PTS-STARTPTS[v3];"
        "[v0][v1][v2][v3]concat=n=4:v=1:a=0[vcat]"
    )
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(s01), "-i", str(s02), "-i", str(s03a), "-i", str(s03b),
        "-filter_complex", v_fc, "-map", "[vcat]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
        str(video_only),
    ])

    v_dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_only),
    ], text=True).strip())
    total_samples = int(round(v_dur * SR))
    vocals_track = np.zeros(total_samples, dtype=np.float32)
    duck_mask = np.zeros(total_samples, dtype=np.float32)

    # 将 5 句 Seed-VC 转换后的原片语气台词精准放入对应口型窗（仅微调 <=1.18x，保持绝对清晰不失真）
    placements = [
        ("c0_trump", 1.22, 3.68),  # 为什么没有黄仁勋的荐章啊
        ("c1_rubio", 4.92, 6.95),  # 总统这话，奴才不明白
        ("c2_rubio", 7.02, 8.06),  # 因为废黄仁勋
        ("c3_rubio", 8.18, 9.68),  # 所以才推荐新CEO
        ("c4_rubio", 9.85, 12.48), # 怎么还会有推举黄仁勋的荐章
    ]
    for key, t_start, t_end in placements:
        clip = vc_clips[key]
        win_dur = t_end - t_start
        # 温和适配窗口，绝不剧烈变速破坏老戏骨顿挫感
        fit = time_stretch(clip, win_dur, min_rate=0.90, max_rate=1.18, sr=SR)
        # 统一每句人声响度到 -16dBFS
        cur_db = rms_db(fit)
        gain = 10.0 ** ((-16.0 - cur_db) / 20.0)
        fit = np.clip(fit * min(3.5, gain), -0.95, 0.95).astype(np.float32)
        s_idx = int(round(t_start * SR))
        e_idx = min(total_samples, s_idx + len(fit))
        seg = fit[:e_idx - s_idx].copy()
        fade = min(int(0.015 * SR), len(seg) // 4)
        if fade > 1:
            seg[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
            seg[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
        vocals_track[s_idx:e_idx] += seg
        duck_mask[s_idx:e_idx] = 1.0
        print(f"  [对轨] {key:10s} -> [{t_start:5.2f}s - {t_start + len(seg)/SR:5.2f}s] (原长 {len(clip)/SR:.2f}s, 窗 {win_dur:.2f}s)", flush=True)

    # 铺回原片清宫配乐（orig_bgm.wav），按剧情节点无缝对应：
    #   [0.00-3.75s] 原片 0.00-3.75s（康熙冷肃静默氛围）
    #   [3.75-12.44s] 原片 3.95-12.64s（万斯处准时切入标志性低沉清宫弦乐「咚——」并托底鲁比奥回话）
    bgm_full = load_mono(orig_bgm_wav, SR)
    bgm_track = np.zeros(total_samples, dtype=np.float32)
    split_s = int(round(3.75 * SR))
    part1 = bgm_full[:split_s]
    part2_start = int(round(3.95 * SR))
    part2_len = total_samples - split_s
    part2 = bgm_full[part2_start:part2_start + part2_len]
    bgm_track[:len(part1)] = part1
    bgm_track[split_s:split_s + len(part2)] = part2

    # 说话时温和闪避 BGM，停顿和万斯反应镜时托起清宫紧张配乐
    win_n = int(0.16 * SR)
    smooth_duck = np.convolve(duck_mask, np.ones(win_n, dtype=np.float32) / win_n, mode="same")
    bgm_gain = 0.72 * (1.0 - smooth_duck) + 0.32 * smooth_duck
    mix_mono = np.clip(vocals_track * 1.05 + bgm_track * bgm_gain, -0.98, 0.98).astype(np.float32)
    mix_raw_wav = save_wav(work_dir / "mix_origtone_raw.wav", mix_mono, SR)

    # 备份干声与混音到项目 outputs/final_cut/
    final_dir = project_dir / "outputs" / "final_cut"
    final_dir.mkdir(parents=True, exist_ok=True)
    save_wav(final_dir / "02_yongzheng_ep12_huang_h3_15s_origtone_vocals_only.wav", vocals_track, SR)

    final_mp4 = final_dir / "02_yongzheng_ep12_huang_h3_15s_origtone_final.mp4"
    run_cmd([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(video_only),
        "-i", str(mix_raw_wav),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-af", "loudnorm=I=-15:TP=-1.5:LRA=9",
        "-c:a", "aac", "-ar", "32000", "-ac", "2", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(final_mp4),
    ])

    probe = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height,sample_rate,channels",
        "-of", "json", str(final_mp4),
    ], text=True)
    print(f"[验收完成] 原片语气+音色替换 15 秒终版已落盘: {final_mp4}", flush=True)
    print(probe, flush=True)
    os.sync()
    time.sleep(3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
