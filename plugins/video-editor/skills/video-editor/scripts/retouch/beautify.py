"""Writes beautify.txt: the filter that adds a soft glow, brighter under-eyes and whiter eye whites.

Run it in the build folder after `mask.py` and the retouch step (`retouched.mp4` exists), with the same
retouch.json. What it adds depends on `beautify` (off, light, medium, strong) and on glow, under_eye and
eye_white in retouch.json (see settings.py). It never adds makeup and never reshapes the face.

  python -I beautify.py [--video retouched.mp4] [--out beautify.txt]

It prints the FFmpeg command: run it, and use the result as the picture before title, captions and
emojis (it belongs where the retouch output goes in the build order). If nothing is on it says so and
writes nothing.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402


def glow_filter(g):
    """The glow on the skin mask: lighter skin that keeps its colour and its hue.

    Lifting brightness alone made skin paler and greyer (medium: 4% lighter, a little less colourful), which viewers
    saw as a grey look next to the original. A whole-picture colour boost to fix it turned rosy cheeks orange. So the
    colour comes back here, on the skin only, in step with the lift, leaning very slightly to red (V) rather than
    yellow (U). On real footage and on light to deep skin tones, the hue stays within about a degree of the original
    at every level, and the colour rises a little with the lightness. Rounded, because truncation shifts the hue."""
    def scale(k):
        return f"'clip(round(128+(val-128)*{1 + k * g:.4f}),0,255)'"
    return f"eq=brightness={g:.4f}:gamma={1 + g * 1.2:.4f},lutyuv=u={scale(4)}:v={scale(4.5)}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", default="retouched.mp4")
    ap.add_argument("--out", default="beautify.txt")
    a = ap.parse_args()
    cfg = settings.load()
    parts = []  # (name, mask file, eq filter)
    if cfg["glow"] > 0:
        g = cfg["glow"]
        parts.append(("glow", "skin.mkv", glow_filter(g)))
    if cfg["under_eye"] > 0:
        u = cfg["under_eye"]
        parts.append(("under", "undereye.mkv", f"eq=brightness={u:.4f}:saturation=0.96"))
    if cfg["eye_white"] > 0:
        w = cfg["eye_white"]
        parts.append(("white", "eyewhite.mkv", f"eq=brightness={w:.4f}:saturation=0.70"))
    if not parts:
        print('Nothing to add: set "beautify" to light, medium or strong in retouch.json (or glow, under_eye, eye_white).')
        return
    for _, mask, _ in parts:
        if not os.path.exists(mask):
            sys.exit(f"{mask} is missing: run mask.py again with this retouch.json (it builds the masks the extras need).")
    n = len(parts)
    lines = ["[0:v]split=%d%s;" % (n + 1, "[b]" + "".join(f"[s{i}]" for i in range(n)))]
    for i, (name, _, eq) in enumerate(parts):
        lines.append(f"[s{i}]{eq},format=yuva444p[{name}0];")
        lines.append(f"[{i + 1}:v]format=gray[{name}m];")
        lines.append(f"[{name}0][{name}m]alphamerge[{name}];")
    last = "b"
    for i, (name, _, _) in enumerate(parts):
        out = "v" if i == n - 1 else f"o{i}"
        tail = ",format=yuv420p" if i == n - 1 else ""
        lines.append(f"[{last}][{name}]overlay=format=yuv444{tail}[{out}];")
        last = out
    lines[-1] = lines[-1].rstrip(";")
    open(a.out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    masks = " ".join(f"-i {m}" for _, m, _ in parts)
    print(f"Wrote {a.out}: {', '.join(p[0] for p in parts)}. Run it (use -filter_complex_script on FFmpeg 6 or older; "
          "add the in-between encoder from my-setup.md):")
    print(f'  ffmpeg -i {a.video} {masks} -/filter_complex {a.out} -map "[v]" -frames:v <frames of {a.video}> '
          "<in-between encoder> beautified.mp4")


if __name__ == "__main__":
    main()
