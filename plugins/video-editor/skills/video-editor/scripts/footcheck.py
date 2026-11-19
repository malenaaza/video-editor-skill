"""Checks how a video was recorded and says what to change in the camera or app for the next recordings.

  python -I footcheck.py <video> [--mains 50] [--shorts] [--target vertical|wide] [--out footcheck.json]

It reads what the file says about itself (ffprobe): the phone or camera, the app when it writes its name, and the
recording settings, and checks them against what the edit needs:
  - frame rate: 25 fps where the mains are 50 Hz (Europe, most of Africa, Asia and South America), 30 where they're
    60 Hz (--mains): other rates make indoor lights flicker or pulse, and mixing rates makes motion stutter;
  - shutter, when the app records it (Blackmagic Camera does): twice the frame rate (1/50 at 25 fps). A very fast
    shutter makes motion choppy and shows lights flickering; a slow one blurs movement;
  - resolution: 4K when Shorts will be cut from a horizontal video (--shorts), so the vertical crop stays sharp;
  - orientation compared with where the video is going (--target);
  - the sound: 44.1 or 48 kHz; 16 kHz or less means the mic reached the phone over Bluetooth (call quality);
  - HDR (HLG or PQ) or Log, which need converting (Rule 8 and references/log.md);
  - the front (selfie) camera, which is smaller and noisier than the back one;
  - a file that was squeezed by a social or messaging app (low bit rate, no camera details), which loses quality.
For each finding it gives the fix in that app's or camera's own words (references/cameras.md has the table and which
apps are confirmed on real files). Nothing is changed: it only reads. Standard library and ffprobe.
"""
import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction

sys.stdout.reconfigure(encoding="utf-8")


# ---- what recorded it ------------------------------------------------------------------------------------------------

def identify(tags, streams):
    """{"app", "device", "lens", "confirmed"} from the container and stream tags (lower-cased keys)."""
    t = {k.lower(): str(v) for k, v in tags.items()}
    handlers = " ".join(str(s.get("tags", {}).get("handler_name", "")) for s in streams).lower()
    encoders = " ".join(str(s.get("tags", {}).get("encoder", "")) for s in streams).lower()
    software = t.get("com.apple.quicktime.software", t.get("software", t.get("encoder", "")))
    model = t.get("com.apple.quicktime.model", t.get("model", t.get("com.android.model", "")))
    make = t.get("com.apple.quicktime.make", t.get("make", t.get("com.android.manufacturer", "")))
    device = model if (not make or make.split()[0].lower() in model.lower()) else f"{make} {model}".strip()
    out = {"app": None, "device": device or None, "lens": None, "confirmed": False}
    if any(k.startswith("com.blackmagic-design") for k in t) or "blackmagic" in software.lower():
        out.update(app="blackmagic", confirmed=True)
        lens = t.get("com.blackmagic-design.camera.lenstype", "")
        out["device"] = model or lens or out["device"]
        out["lens"] = "front" if "front" in (lens + model).lower() else ("back" if lens else None)
    elif "final cut camera" in software.lower():
        out["app"] = "final_cut_camera"
    elif make.lower().startswith("apple") or "iphone" in model.lower() or "com.apple.quicktime.model" in t:
        out["app"] = "apple_camera"
        out["lens"] = "front" if "front" in model.lower() else None
    elif "com.android.version" in t or make.lower() in ("samsung", "google") or "android" in software.lower():
        out["app"] = "android_camera"
    elif "gopro" in handlers or "gopro" in encoders or "firmware" in t and t.get("firmware", "").upper().startswith("H"):
        out["app"] = "gopro"
    elif "dji" in handlers or "dji" in encoders or "dji" in software.lower():
        out["app"] = "dji"
    elif "xavc" in t.get("major_brand", "").lower() or "sony" in make.lower():
        out["app"] = "sony"
    return out


# ---- the checks --------------------------------------------------------------------------------------------------------

STEPS = {
    "fps": {
        "blackmagic": "tap the frame rate at the top of the screen and choose {fps}",
        "final_cut_camera": "in the recording settings, choose {fps} fps",
        "apple_camera": "Settings > Camera > Record Video: turn on Show PAL Formats if you need 25 fps, then choose "
                        "4K at {fps} fps",
        "android_camera": "in Pro video mode, choose {fps} fps (if {fps} isn't offered, use 30 and check your lights "
                          "don't flicker)",
        "sony": "for 25p set the NTSC/PAL Selector (Setup menu) to PAL, then choose 25p in the movie record setting",
        "gopro": "in Preferences set Video Format (or Anti-Flicker) to {mains} Hz / {format}, then choose {fps} fps",
        "dji": "in the camera settings set Anti-flicker to {mains} Hz and the frame rate to {fps} fps",
    },
    "shutter": {
        "blackmagic": "tap the shutter value at the top and set 1/{shutter} (or a 180° shutter angle)",
        "final_cut_camera": "set the shutter to 1/{shutter} in manual controls",
        "android_camera": "in Pro video mode set the shutter (S) to 1/{shutter}",
        "sony": "in movie mode set the shutter speed to 1/{shutter}",
    },
    "resolution": {
        "blackmagic": "tap the resolution at the top and choose 4K (3840x2160)",
        "final_cut_camera": "choose 4K in the recording settings",
        "apple_camera": "Settings > Camera > Record Video: choose 4K",
        "android_camera": "choose UHD / 4K in the video size setting",
        "sony": "choose XAVC S 4K in the file format setting",
        "gopro": "choose 4K in the video settings",
        "dji": "choose 4K in the video settings",
    },
    "hdr": {
        "blackmagic": "if HDR is on in the app's settings, record SDR (Rec.709) instead, unless you colour-grade "
                      "HDR yourself",
        "apple_camera": "Settings > Camera > Record Video: turn off HDR Video",
        "android_camera": "turn off HDR10+ / HDR video in the camera settings",
    },
    "front": {
        "blackmagic": "switch to the back main camera (1x lens); to see yourself, monitor from a second phone or tablet "
                      "with the Blackmagic Camera app's remote monitoring",
        "apple_camera": "film with the back main camera (1x); the front one is fine when you need to see the screen",
    },
    "bluetooth": {
        "": "connect the mic's receiver to the phone or camera by its plug or cable instead of Bluetooth; Bluetooth "
            "limits the sound to call quality",
    },
}


def step(kind, app, **values):
    table = STEPS.get(kind, {})
    text = table.get(app or "") or table.get("") or "change it in the camera or app's settings"
    return text.format(**values)


def parse_shutter(text):
    """1/613 -> 613.0; anything else (an angle, nothing) -> None."""
    m = re.match(r"^\s*1\s*/\s*([\d.]+)", text or "")
    return float(m.group(1)) if m else None


def check(info, mains=50, shorts=False, target=None):
    """(identity, findings) from ffprobe's JSON. findings: [{"what", "found", "fix"}]."""
    streams = info.get("streams", [])
    tags = info.get("format", {}).get("tags", {})
    who = identify(tags, streams)
    app = who["app"]
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    findings = []
    if not video:
        return who, [{"what": "no picture", "found": "the file has no video", "fix": "check the file"}]
    want_fps = 25 if mains == 50 else 30
    fps = float(Fraction(video.get("r_frame_rate", "0/1"))) if video.get("r_frame_rate", "0/0") != "0/0" else 0
    fmt = "PAL" if mains == 50 else "NTSC"
    if fps and abs(fps - want_fps) > 0.2 and abs(fps - 2 * want_fps) > 0.2:
        findings.append({"what": "frame rate", "found": f"{fps:g} fps",
                         "fix": f"{want_fps} fps for {mains} Hz lights: " +
                                step("fps", app, fps=want_fps, mains=mains, format=fmt)})
    t = {k.lower(): str(v) for k, v in tags.items()}
    shutter = parse_shutter(t.get("com.blackmagic-design.shutterspeed", ""))
    base = fps if fps else want_fps
    target_fps = want_fps if findings and findings[0]["what"] == "frame rate" else base
    if shutter:
        ideal = 2 * target_fps
        if shutter > ideal * 3 or shutter < ideal / 1.6:
            effect = "motion looks choppy and lights can flicker" if shutter > ideal else "movement blurs"
            findings.append({"what": "shutter", "found": f"1/{shutter:g} ({effect})",
                             "fix": step("shutter", app, shutter=int(round(ideal)))})
    w, h = int(video.get("width", 0)), int(video.get("height", 0))
    rotation = 0
    for sd in video.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = abs(int(float(sd["rotation"])))
    if rotation in (90, 270):
        w, h = h, w
    if shorts and w > h and h < 2160:
        findings.append({"what": "resolution", "found": f"{w}x{h}",
                         "fix": "4K, so the Shorts cut from this horizontal video stay sharp: " + step("resolution", app)})
    if target == "vertical" and w > h:
        findings.append({"what": "orientation", "found": "horizontal",
                         "fix": "for Reels and TikTok alone, film vertical; horizontal is right when the same "
                                "recording also makes a YouTube video (the Shorts are cropped from it)"})
    elif target == "wide" and h > w:
        findings.append({"what": "orientation", "found": "vertical",
                         "fix": "for YouTube, film horizontal (16:9)"})
    transfer = str(video.get("color_transfer", "")).lower()
    if transfer in ("arib-std-b67", "smpte2084"):
        findings.append({"what": "HDR", "found": "HLG" if transfer == "arib-std-b67" else "PQ (HDR10)",
                         "fix": "the skill converts it (Rule 8), but SDR is simpler and looks the same on most phones: "
                                + step("hdr", app)})
    if who["lens"] == "front":
        findings.append({"what": "camera", "found": "front (selfie) camera",
                         "fix": "the back camera has a bigger sensor: sharper, less noise in indoor light; "
                                + step("front", app)})
    if audio:
        rate = int(audio.get("sample_rate", 0) or 0)
        if 0 < rate <= 24000:
            findings.append({"what": "sound", "found": f"{rate / 1000:g} kHz (call quality)",
                             "fix": step("bluetooth", None)})
    else:
        findings.append({"what": "sound", "found": "no sound in the file", "fix": "check the mic and the app's audio input"})
    bitrate = int(info.get("format", {}).get("bit_rate", 0) or 0)
    pixels = w * h
    if not app and bitrate and pixels and bitrate / pixels < 1.5:      # under ~3 Mbps for 1080p: squeezed
        findings.append({"what": "quality", "found": f"{bitrate / 1e6:.1f} Mbps with no camera details",
                         "fix": "it looks recorded or saved through a social or messaging app (Instagram, TikTok, "
                                "CapCut, WhatsApp), which squeezes it: record with the camera app and send the "
                                "original file"})
    return who, findings


APP_NAMES = {"blackmagic": "Blackmagic Camera app", "final_cut_camera": "Final Cut Camera", "apple_camera":
             "iPhone Camera app", "android_camera": "Android camera app", "gopro": "GoPro", "dji": "DJI camera",
             "sony": "Sony camera"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--mains", type=int, choices=(50, 60), default=50, help="the mains frequency where they film")
    ap.add_argument("--shorts", action="store_true", help="Shorts will be cropped from this horizontal video")
    ap.add_argument("--target", choices=("vertical", "wide"))
    ap.add_argument("--out", default="footcheck.json")
    a = ap.parse_args()

    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", a.video],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"Can't read {a.video}: {r.stderr.strip()}")
    who, findings = check(json.loads(r.stdout), a.mains, a.shorts, a.target)
    name = APP_NAMES.get(who["app"], "an app or camera the file doesn't name")
    print(f"Recorded with: {name}" + (f", {who['device']}" if who["device"] else "")
          + ("" if who["confirmed"] or not who["app"] else " (recognised from the file; the steps below are from the "
             "app's documentation)"))
    if not who["app"]:
        print("Ask the user once which app or camera they recorded with, and save it in my-setup.md.")
    if not findings:
        print("Nothing to change: the settings suit this edit.")
    for f in findings:
        print(f"- {f['what']}: {f['found']}. {f['fix'][0].upper()}{f['fix'][1:]}.")
    json.dump({"recorded_with": who, "findings": findings}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False,
              indent=1)
    print(f"Wrote {a.out}.")


if __name__ == "__main__":
    main()
