"""Measures a colour cast (white balance) instead of judging it by eye, and gives the FFmpeg filter that removes it.

  python -I balance.py <video or image> [--region x,y,w,h] [--check before-after.png]

It samples 8 frames across the video (or the one image) and keeps the pixels that should be neutral: low
saturation, neither dark nor clipped, and not skin. Their average colour shows the cast: a white wall that comes out
blue, or a grey shirt that comes out green. It prints the cast in plain words and its size, and the filter that brings
those pixels back to neutral without changing the brightness (a `colorchannelmixer`, each channel changed by at most
8 %). Below 1.5 % it says no correction is needed.

If the neutral areas in the shot aren't really neutral (a beige wall, a cream sofa), the measure follows them: point
it at something you know is white or grey with --region (fractions of the frame: x,y,width,height, for example
0.05,0.1,0.2,0.2 for a white shelf at the top left). --check writes the middle frame before and after, side by side.
Use it on the source of the clean render (after the LUT for Log footage), and put the filter before the brand's colour
boost. Needs numpy and FFmpeg.
"""
import argparse
import json
import subprocess
import sys

import numpy as np

SIZE = 480  # frames are measured at 480 x 480: colour averages don't need the full picture

sys.stdout.reconfigure(encoding="utf-8")


def duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out)
    except (ValueError, OSError, subprocess.SubprocessError):
        return 0.0


def grab(path, at):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{at:.3f}", "-i", path, "-frames:v", "1", "-vf",
                          f"scale={SIZE}:{SIZE}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, timeout=120).stdout
    if len(raw) != SIZE * SIZE * 3:
        return None
    return np.frombuffer(raw, np.uint8).reshape(SIZE, SIZE, 3).astype(np.float32) / 255


def neutral_pixels(rgb, region=None):
    if region:
        x, y, w, h = region
        rgb = rgb[int(y * SIZE):int((y + h) * SIZE), int(x * SIZE):int((x + w) * SIZE)]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    hi, lo = rgb.max(axis=2), rgb.min(axis=2)
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    sat = (hi - lo) / np.maximum(hi, 1e-6)
    cr = 128 + 255 * (0.5 * r - 0.4187 * g - 0.0813 * b)
    cb = 128 + 255 * (-0.1687 * r - 0.3313 * g + 0.5 * b)
    skin = (cr > 135) & (cr < 175) & (cb > 80) & (cb < 125)
    keep = (luma > 0.25) & (hi < 0.98) & (sat < (0.30 if region else 0.18)) & ~skin
    return rgb[keep]


def measure(path, region=None, samples=8):
    length = duration(path)
    times = [length * (i + 0.5) / samples for i in range(samples)] if length > 0.5 else [0.0]
    pixels, frames = [], 0
    for t in times:
        frame = grab(path, t)
        if frame is None:
            continue
        frames += 1
        pixels.append(neutral_pixels(frame, region))
    if not frames:
        sys.exit(f"Can't read {path}.")
    pixels = np.concatenate(pixels) if pixels else np.zeros((0, 3), np.float32)
    total = frames * SIZE * SIZE if not region else frames * region[2] * region[3] * SIZE * SIZE
    share = len(pixels) / max(total, 1)
    if len(pixels) < 200 or share < 0.005:
        return {"ok": False, "share": round(share * 100, 2), "frames": frames}
    mean = np.median(pixels, axis=0)  # median: robust to a few coloured pixels that slipped in
    gray = mean.mean()
    gains = np.clip(gray / np.maximum(mean, 1e-6), 0.92, 1.08)
    weights = np.array([0.2126, 0.7152, 0.0722])
    gains *= (weights @ mean) / (weights @ (mean * gains))  # keep the brightness
    deviation = mean / gray - 1
    return {"ok": True, "frames": frames, "share": round(share * 100, 2), "mean": [round(float(v), 4) for v in mean],
            "deviation": [round(float(v) * 100, 2) for v in deviation], "gains": [round(float(v), 4) for v in gains],
            "size": round(float(np.abs(gains - 1).max()) * 100, 2)}


def describe(result):
    size = result["size"]
    if size < 1.5:
        return "no colour cast worth correcting"
    r, g, b = result["deviation"]
    warm_cool = r - b  # how photographers describe a cast: warm or cool, and green or magenta
    green_magenta = g - (r + b) / 2
    if abs(warm_cool) >= abs(green_magenta):
        name = "warm (orange)" if warm_cool > 0 else "cool (blue)"
    else:
        name = "green" if green_magenta > 0 else "magenta (pink)"
    words = "slight" if size < 3 else "noticeable" if size < 6 else "strong"
    return f"{words} {name} cast"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--region", help="x,y,width,height as fractions of the frame: something known to be white or grey")
    ap.add_argument("--check", help="write the middle frame before and after, side by side")
    a = ap.parse_args()
    region = [float(v) for v in a.region.split(",")] if a.region else None
    if region and (len(region) != 4 or not all(0 <= v <= 1 for v in region)):
        sys.exit("--region needs four fractions: x,y,width,height (for example 0.05,0.1,0.2,0.2).")
    result = measure(a.source, region)
    if not result["ok"]:
        print(f"Can't measure: only {result['share']}% of the picture is neutral (white or grey). Point it at something "
              "white or grey with --region, or leave the colour as it is.")
        return
    filt = "colorchannelmixer=rr={:.4f}:gg={:.4f}:bb={:.4f}".format(*result["gains"])
    print(f"Measured on {result['frames']} frame(s), {result['share']}% of the picture neutral: {describe(result)} "
          f"({result['size']}%).")
    if result["size"] < 1.5:
        print("No correction needed.")
    else:
        print(f"Filter, before the brand's colour boost: {filt}")
        if a.check:
            mid = duration(a.source) / 2
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{mid:.3f}", "-i", a.source, "-frames:v", "1",
                            "-filter_complex", f"[0:v]scale=640:-2,split[a][b];[b]{filt}[c];[a][c]hstack",
                            a.check], check=True)
            print(f"Before and after: {a.check}")
    print(json.dumps({"cast": describe(result), "size_percent": result["size"],
                      "filter": filt if result["size"] >= 1.5 else None}))


if __name__ == "__main__":
    main()
