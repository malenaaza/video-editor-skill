"""Makes a clip from a second camera (an iPhone used for some lines) match the main camera, so the clips join
without a jump in frame rate, size, brightness range or sound. The original is never changed.

  python -I conform.py <second clip> --like <main camera clip>            write <name>-conformed.mov next to it
  python -I conform.py <second clip> --like <main camera clip> --check    only say what differs; writes nothing
  options: --out <file>, --fit crop|pad, --encoder "<in-between encoder from my-setup.md>"

What it changes, and why:
- Frame rate: to exactly the main camera's, at a constant rate. Phones record a variable rate (the time between
  frames changes with the light), which lets the sound drift against the picture and makes the joins uneven. A
  different rate (30 against 25) is converted by dropping or repeating frames, which can judder on movement: tell
  the user once to film at the same rate (iPhone: Settings > Camera > Record Video, Show PAL Formats, 25 fps).
- Size and shape: scaled to the main camera's size. When the shape differs (vertical against horizontal) it is
  cropped to fill (--fit crop, the default) or put on bars (--fit pad), and that is said.
- HDR (HLG, which iPhones record by default, or PQ): tone mapped to SDR Rec.709, because next to an SDR clip it
  looks washed out or too bright. Needs FFmpeg's zscale; without it, it says so and leaves the HDR.
- Colour tags and pixel format: the main camera's, so later steps read both clips the same way.
- Sound: resampled to the main camera's sample rate and channels. Its loudness is matched later, when the clips'
  voices are joined (voice/leveljoin.py).
Not matched here: the cameras' different colour (white balance, contrast, saturation). Correct that by eye in the
grade, on a frame of each.

Standard library, FFmpeg and ffprobe only.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from fractions import Fraction

HDR = {"arib-std-b67": "HLG", "smpte2084": "PQ (HDR10 or Dolby Vision)"}
DEFAULT_ENCODER = "-c:v libx264 -crf 14 -preset medium"


def probe(path):
    """What the conforming needs to know about a clip, from ffprobe."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"Can't read {path}: {r.stderr.strip()}")
    data = json.loads(r.stdout)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    if video is None:
        sys.exit(f"{path} has no video.")
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    rotation = 0
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotation = int(float(side["rotation"]))
    rotation = rotation or int(float(video.get("tags", {}).get("rotate", 0)))
    width, height = int(video["width"]), int(video["height"])
    if abs(rotation) % 180 == 90:  # FFmpeg turns the picture upright when decoding
        width, height = height, width

    def rate(text):
        try:
            value = Fraction(text)
        except (ValueError, ZeroDivisionError):
            return None
        return value if value > 0 else None

    nominal = rate(video.get("r_frame_rate", "0/0"))
    average = rate(video.get("avg_frame_rate", "0/0"))
    fps = nominal or average or Fraction(25)
    variable = bool(nominal and average and abs(float(nominal) - float(average)) / float(nominal) > 0.005)
    return {"width": width, "height": height, "fps": fps, "variable": variable,
            "pix_fmt": video.get("pix_fmt", "yuv420p"), "transfer": video.get("color_transfer"),
            "primaries": video.get("color_primaries"), "matrix": video.get("color_space"),
            "rate": int(audio["sample_rate"]) if audio else None, "channels": int(audio.get("channels", 2)) if audio else None,
            "duration": float(data.get("format", {}).get("duration", 0) or 0)}


def show_fps(value):
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def has_filter(name):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return any(line.split()[1:2] == [name] for line in out.splitlines() if line.strip())


def plan(main, clip, fit="crop", zscale=True):
    """(differences to tell the user, video filter, audio filter, output colour tags)."""
    notes, vf = [], []
    tags = {"color_primaries": main["primaries"] or "bt709", "color_trc": main["transfer"] or "bt709",
            "colorspace": main["matrix"] or "bt709"}
    hdr = HDR.get(clip["transfer"])
    if hdr and not HDR.get(main["transfer"]):
        if zscale:
            tin = clip["transfer"]
            pin = clip["primaries"] or "bt2020"
            min_ = clip["matrix"] or "bt2020nc"
            vf.append(f"zscale=tin={tin}:pin={pin}:min={min_}:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                      "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv")
            notes.append(f"HDR ({hdr}) converted to normal SDR, like the main camera. Next time: Settings > Camera > "
                         "Record Video, turn off HDR Video.")
        else:
            notes.append(f"HDR ({hdr}) NOT converted: this FFmpeg has no zscale filter. It will look washed out "
                         "next to the main camera; install a full FFmpeg build or turn HDR off on the phone.")
            tags = {}
    if clip["variable"] or clip["fps"] != main["fps"]:
        if clip["fps"] != main["fps"]:
            notes.append(f"Frame rate {show_fps(clip['fps'])} -> {show_fps(main['fps'])} fps (frames dropped or repeated; "
                         "film at the same rate as the main camera next time).")
        else:
            notes.append(f"Variable frame rate made constant at {show_fps(main['fps'])} fps, so the sound can't drift.")
    vf.append(f"fps={main['fps']}")
    W, H = main["width"], main["height"]
    if (clip["width"], clip["height"]) != (W, H):
        same_shape = abs(clip["width"] / clip["height"] - W / H) < 0.01
        if same_shape:
            notes.append(f"Size {clip['width']}x{clip['height']} -> {W}x{H}.")
            vf.append(f"scale={W}:{H}:flags=lanczos")
        elif fit == "pad":
            notes.append(f"Shape differs ({clip['width']}x{clip['height']} against {W}x{H}): fitted inside, with bars.")
            vf.append(f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")
        else:
            notes.append(f"Shape differs ({clip['width']}x{clip['height']} against {W}x{H}): cropped to fill. Check the "
                         "head isn't cut, or use --fit pad. Film both cameras the same way round next time.")
            vf.append(f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}")
    vf.append(f"setsar=1,format={main['pix_fmt']}")
    af = None
    if main["rate"] and clip["rate"]:
        af = f"aresample={main['rate']}"
        if clip["rate"] != main["rate"] or clip["channels"] != main["channels"]:
            notes.append(f"Sound {clip['rate']} Hz, {clip['channels']} ch -> {main['rate']} Hz, {main['channels']} ch.")
    elif main["rate"] and not clip["rate"]:
        notes.append("This clip has no sound: the voice for it must come from another recording.")
    return notes, ",".join(vf), af, tags


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", help="the clip from the second camera")
    ap.add_argument("--like", required=True, help="a clip from the main camera, to match")
    ap.add_argument("--out", help="default: <clip name>-conformed.mov next to the clip")
    ap.add_argument("--fit", choices=("crop", "pad"), default="crop", help="when the shape differs (default crop)")
    ap.add_argument("--encoder", default=DEFAULT_ENCODER, help=f'video encoder options (default "{DEFAULT_ENCODER}")')
    ap.add_argument("--check", action="store_true", help="only say what differs")
    a = ap.parse_args()
    main_info, clip_info = probe(a.like), probe(a.clip)
    notes, vf, af, tags = plan(main_info, clip_info, a.fit, has_filter("zscale"))
    if not notes:
        print("This clip already matches the main camera: nothing to change.")
        return
    print(f"{os.path.basename(a.clip)} against the main camera ({os.path.basename(a.like)}):")
    for note in notes:
        print("  - " + note)
    if a.check:
        return
    out = a.out or os.path.splitext(a.clip)[0] + "-conformed.mov"
    if os.path.abspath(out) == os.path.abspath(a.clip):
        sys.exit("--out must be a new file: the original is never overwritten.")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", a.clip, "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf]
    cmd += shlex.split(a.encoder)
    for key, value in tags.items():
        cmd += [f"-{key}", value]
    if af:
        cmd += ["-af", af, "-ac", str(main_info["channels"]), "-c:a", "pcm_s16le"]
    r = subprocess.run(cmd + [out])
    if r.returncode:
        sys.exit("FFmpeg failed: nothing was written.")
    done = probe(out)
    print(f"Wrote {out}: {done['width']}x{done['height']}, {show_fps(done['fps'])} fps, {done['duration']:.2f} s.")
    print("Use it instead of the original clip from here on (transcribe, cut, retouch), and correct its colour by "
          "eye against the main camera in the grade.")


if __name__ == "__main__":
    main()
