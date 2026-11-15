"""Measure background noise in a voice recording, then clean and polish the voice.

Usage:
  python -I clean_voice.py measure <audio or video>
  python -I clean_voice.py clean <in> <out.wav> --strength light|strong [--hum 50|60]
                                 [--engine auto|deepfilter|rnnoise|ffmpeg] [--no-polish]
                                 [--rnnoise-model <cb.rnnn>] [--deep-filter <program>]

measure  prints the noise floor (the quietest moments, between words), the speech level,
         the gap between them, any mains hum (50 or 60 Hz) and low rumble, then a
         suggested strength: none, light or strong. Run it on the original recording, which
         still has its pauses: after pause cutting there's nothing left to measure the noise in.
clean    in this order:
         1. before noise removal: cut rumble under 80 Hz, notch out mains hum (--hum), and even
            out loud and quiet words gently. Compressing first means the leftover noise isn't
            raised afterwards.
         2. noise removal, with the first engine that's available:
            - deepfilter: DeepFilterNet's standalone program, deep-filter (best for voices);
            - rnnoise: FFmpeg's arnndn filter with an RNNoise model file (very good for voices);
            - ffmpeg: FFmpeg's afftdn (weak, last resort).
            "light" leaves some room sound so the voice stays natural; "strong" removes as
            much as it can. If the voice itself gets more than 3 dB quieter, which means the
            engine took part of the voice for noise, it retries more gently, then falls back.
         3. after noise removal: soften harsh "s" sounds, add a little clarity around 3 kHz,
            and catch peaks.
         --no-polish skips steps 1 (except hum) and 3.
         Writes a mono 48 kHz 16-bit WAV. It doesn't set the final loudness: level the result
         afterwards with loudnorm (SKILL.md, Rule 7).

Needs FFmpeg on the PATH and numpy. Optional, in order of preference:
  deep-filter: one file from github.com/Rikorose/DeepFilterNet/releases, no Python packages.
  RNNoise model: cb.rnnn from github.com/GregorR/rnnoise-models (conjoined-burgers), saved as
  ~/.video-editor/models/cb.rnnn.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

RATE = 48000
DEFAULT_MODEL = os.path.join(os.path.expanduser("~"), ".video-editor", "models", "cb.rnnn")


def decode(path: str, rate: int = RATE) -> np.ndarray:
    """Decode any audio or video file to mono float32 at the given rate."""
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def measure(path: str) -> dict:
    rate = 16000
    a = decode(path, rate)
    frame = rate // 20  # 50 ms
    n = len(a) // frame
    if n < 20:
        sys.exit("Too short to measure: need at least 1 second of audio.")
    frames = a[: n * frame].reshape(n, frame)
    levels = 20 * np.log10(np.sqrt((frames**2).mean(axis=1) + 1e-12))
    floor = float(np.percentile(levels, 10))
    speech = float(np.percentile(levels, 90))

    # Hum is steady, so a 1-second spectrum (1 Hz steps), taking the median over the whole
    # recording, shows it as sharp peaks while speech averages out.
    hum, rumble = None, float("nan")
    count = len(a) // rate
    if count >= 2:
        segs = a[: count * rate].reshape(count, rate) * np.hanning(rate)
        spectrum = np.median(np.abs(np.fft.rfft(segs, axis=1)) ** 2, axis=0)
        freqs = np.fft.rfftfreq(rate, 1 / rate)

        def peak_over_neighbors(f0):
            i = int(round(f0))
            neighbors = np.r_[spectrum[i - 12: i - 3], spectrum[i + 4: i + 13]]
            return 10 * np.log10((spectrum[i - 1: i + 2].max() + 1e-20) / (np.median(neighbors) + 1e-20))

        hum50 = np.mean([peak_over_neighbors(f) for f in (50, 100, 150)])
        hum60 = np.mean([peak_over_neighbors(f) for f in (60, 120, 180)])
        hum = 50 if hum50 > 10 and hum50 >= hum60 else 60 if hum60 > 10 else None
        low = spectrum[(freqs > 20) & (freqs < 80)].sum()
        rest = spectrum[(freqs >= 80) & (freqs < 8000)].sum()
        rumble = float(10 * np.log10((low + 1e-20) / (rest + 1e-20)))

    gap = speech - floor
    suggestion = "none" if gap >= 45 else "light" if gap >= 30 else "strong"
    return {
        "noise_floor_db": round(floor, 1),
        "speech_db": round(speech, 1),
        "gap_db": round(gap, 1),
        "hum_hz": hum,
        "rumble_db": round(rumble, 1),
        "suggested_strength": suggestion,
    }


def ffmpeg(args: list, cwd: str = None) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, check=True, cwd=cwd)


def pre_filter(strength: str, hum, polish: bool) -> str:
    parts = ["highpass=f=80:poles=2"] if polish else []
    if hum:
        parts += [f"bandreject=f={hum * k}:width_type=q:w=30" for k in (1, 2, 3)]
    if polish:
        ratio = 2 if strength == "light" else 3
        parts.append(f"acompressor=threshold=-24dB:ratio={ratio}:attack=10:release=150:makeup=2")
    return ",".join(parts) or "anull"


def post_filter(strength: str) -> str:
    light = strength == "light"
    return ",".join([
        f"deesser=i={0.3 if light else 0.5}:m=0.5:f=0.5",
        f"equalizer=f=3000:width_type=o:w=1.5:g={1.5 if light else 2.5}",
        "alimiter=limit=0.95:level=false",
    ])


def run_deepfilter(src: str, dst: str, strength: str, program: str, gentle: bool) -> None:
    exe = shutil.which(program) or (program if os.path.isfile(program) else None)
    if exe is None:
        raise FileNotFoundError(f"deep-filter not found ({program})")
    outdir = os.path.join(os.path.dirname(dst), "df-out")
    os.makedirs(outdir, exist_ok=True)
    cmd = [exe, "-o", outdir]
    limit = 6 if gentle else 12 if strength == "light" else None  # most dB of noise to remove
    if limit is not None:
        cmd += ["-a", str(limit)]
    subprocess.run(cmd + [src], check=True, capture_output=True)
    produced = os.path.join(outdir, os.path.basename(src))
    if not os.path.isfile(produced):
        raise RuntimeError("deep-filter wrote no output file")
    os.replace(produced, dst)


def run_rnnoise(src: str, dst: str, strength: str, model: str, gentle: bool) -> None:
    if not os.path.isfile(model):
        raise FileNotFoundError(f"RNNoise model not found ({model})")
    # Run from the temp folder with a bare file name: Windows paths break FFmpeg filter options.
    tmp = os.path.dirname(dst)
    shutil.copy(model, os.path.join(tmp, "model.rnnn"))
    mix = 0.4 if gentle else 0.7 if strength == "light" else 1.0
    ffmpeg(["-i", src, "-af", f"arnndn=m=model.rnnn:mix={mix}", "-c:a", "pcm_s16le", dst], cwd=tmp)


def run_afftdn(src: str, dst: str, strength: str, floor_db: float, gentle: bool) -> None:
    nr = 6 if gentle else 12 if strength == "light" else 24
    nf = max(-80, min(-20, round(floor_db)))
    ffmpeg(["-i", src, "-af", f"afftdn=nr={nr}:nf={nf}", "-c:a", "pcm_s16le", dst])


def speech_level(path: str) -> float:
    a = decode(path, 16000)
    frame = 800
    n = len(a) // frame
    levels = 20 * np.log10(np.sqrt((a[: n * frame].reshape(n, frame) ** 2).mean(axis=1) + 1e-12))
    return float(np.percentile(levels, 90))


def clean(args) -> None:
    info = measure(args.input)
    print(f"Before: noise floor {info['noise_floor_db']} dB, speech {info['speech_db']} dB, "
          f"gap {info['gap_db']} dB, hum {info['hum_hz'] or 'none'}")
    polish = not args.no_polish
    with tempfile.TemporaryDirectory() as tmp:
        pre = os.path.join(tmp, "pre.wav")
        den = os.path.join(tmp, "denoised.wav")
        ffmpeg(["-i", args.input, "-vn", "-ac", "1", "-ar", str(RATE),
                "-af", pre_filter(args.strength, args.hum, polish), "-c:a", "pcm_s16le", pre])
        before = speech_level(pre)

        engines = ["deepfilter", "rnnoise", "ffmpeg"] if args.engine == "auto" else [args.engine]
        used = None
        for engine in engines:
            for gentle in (False, True):
                try:
                    if engine == "deepfilter":
                        run_deepfilter(pre, den, args.strength, args.deep_filter, gentle)
                    elif engine == "rnnoise":
                        run_rnnoise(pre, den, args.strength, args.rnnoise_model, gentle)
                    else:
                        run_afftdn(pre, den, args.strength, info["noise_floor_db"], gentle)
                except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as err:
                    if args.engine != "auto":
                        sys.exit(f"{engine} failed: {err}")
                    if not isinstance(err, FileNotFoundError):
                        print(f"{engine} failed ({err}); trying the next engine.")
                    break
                drop = before - speech_level(den)
                if drop <= 3:
                    used = f"{engine}{' (gentler)' if gentle else ''}"
                    break
                print(f"{engine}{' (gentler)' if gentle else ''} made the voice {drop:.1f} dB quieter: "
                      f"it took part of the voice for noise.")
            if used:
                break
        if not used:
            print("No engine cleaned the noise without hurting the voice: keeping the voice without noise removal.")
            shutil.copy(pre, den)
            used = "none"

        post = ["-af", post_filter(args.strength)] if polish else []
        ffmpeg(["-i", den] + post + ["-ar", str(RATE), "-c:a", "pcm_s16le", args.output])

    after = measure(args.output)
    print(f"Noise removal: {used}, strength {args.strength}, polish {'on' if polish else 'off'}")
    print(f"After: noise floor {after['noise_floor_db']} dB, speech {after['speech_db']} dB, "
          f"gap {after['gap_db']} dB, hum {after['hum_hz'] or 'none'}")
    print(f"Saved {args.output}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("input")
    c = sub.add_parser("clean")
    c.add_argument("input")
    c.add_argument("output")
    c.add_argument("--strength", choices=["light", "strong"], default="light")
    c.add_argument("--hum", type=int, choices=[50, 60])
    c.add_argument("--engine", choices=["auto", "deepfilter", "rnnoise", "ffmpeg"], default="auto")
    c.add_argument("--no-polish", action="store_true")
    c.add_argument("--rnnoise-model", default=DEFAULT_MODEL)
    c.add_argument("--deep-filter", default="deep-filter", help="path to the deep-filter program")
    args = ap.parse_args()
    if args.cmd == "measure":
        for k, v in measure(args.input).items():
            print(f"{k}: {v}")
    else:
        clean(args)


if __name__ == "__main__":
    main()
