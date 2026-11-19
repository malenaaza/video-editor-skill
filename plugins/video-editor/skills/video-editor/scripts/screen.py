"""Screen recordings for tutorials: a smooth zoom onto the part of the screen that matters, and a vertical layout
with the screen on top and the speaker below, for Shorts.

  python -I screen.py suggest <screen video> [--every 0.5] [--out zooms.json] [--sheet zooms.png]
  python -I screen.py zoom <screen video> zooms.json [--move 0.8] [--max-zoom 2.5] [--out zoom.txt]
  <face python> -I screen.py stack <screen video> <camera video> [--face-model face_landmarker.task]
                [--face-x 1900] [--size 1080x1920] [--split 0.5] [--audio camera] [--out stack.txt]

suggest: looks at what changes on the screen every --every seconds (typing, a menu opening, a result appearing) and
writes zooms.json, one entry each time the place of the action changes:
  [{"at": 0.0, "box": "full"}, {"at": 4.5, "box": [x, y, w, h]}, {"at": 12.0, "box": "full"}, ...]
A change over most of the screen (a new page) zooms back out to "full"; the mouse alone doesn't count. It's a
suggestion: look at zooms.png (the boxes drawn on the frames, with their times), then fix, merge or delete entries.
Boxes are in the screen video's pixels; "full" is the whole screen.

zoom: writes zoom.txt, one filter line that eases from one box to the next over --move seconds, starting at each "at"
and holding until the next. Each box is widened to the video's shape and kept inside the frame; it never zooms in
more than --max-zoom (2.5: beyond that, text gets soft and viewers lose their place). Drawn with sub-pixel precision
(FFmpeg's perspective filter), so slow zooms don't shake. For the vertical layout, keep the action near the middle of
each box: the top panel shows the middle of the zoomed picture.

stack: writes stack.txt, a -filter_complex script with the screen (input 0) on top and the speaker (input 1) below,
each cropped to fill its half of the vertical frame (--split is the screen's share of the height). The speaker is
centred on their face (found with MediaPipe when --face-model is given, or at --face-x, or the middle). Use the
zoomed screen video as input 0. The two recordings must already be in sync and the same length (cut them to the same
moment first). Sound comes from --audio (camera or screen). Needs FFmpeg; stack's face finding needs OpenCV and
MediaPipe.
"""
import argparse
import json
import os
import subprocess
import sys
from fractions import Fraction

sys.stdout.reconfigure(encoding="utf-8")


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", video],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"Can't read {video}: {out.stderr.strip()}")
    info = json.loads(out.stdout)
    s = info["streams"][0]
    return s["width"], s["height"], float(Fraction(s["r_frame_rate"])), float(info["format"]["duration"])


# ---- suggest -------------------------------------------------------------------------------------------------------

def change_box(prev, cur, threshold=24, min_pixels=40):
    """Bounding box (x, y, w, h) of what changed between two grey frames (numpy arrays), or None. Lone small specks
    (the mouse pointer, a blinking cursor) are ignored."""
    import numpy as np
    diff = np.abs(cur.astype(np.int16) - prev.astype(np.int16)) > threshold
    if diff.sum() < min_pixels:
        return None
    rows, cols = np.where(diff.any(axis=1))[0], np.where(diff.any(axis=0))[0]
    x0, x1, y0, y1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1
    if (x1 - x0) * (y1 - y0) < 4 * min_pixels and diff.sum() < 2 * min_pixels:
        return None                                        # a pointer-sized blip
    return int(x0), int(y0), int(x1 - x0), int(y1 - y0)


def plan_zooms(changes, width, height, full_share=0.45, gap=1.5, near=0.25):
    """Zoom entries from [(time, box or None)]. A box covering more than full_share of the screen means "full";
    boxes that keep landing near each other are merged into one; after `gap` seconds of nothing new the zoom holds."""
    def union(a, b):
        x0, y0 = min(a[0], b[0]), min(a[1], b[1])
        return x0, y0, max(a[0] + a[2], b[0] + b[2]) - x0, max(a[1] + a[3], b[1] + b[3]) - y0

    def centre(b):
        return b[0] + b[2] / 2, b[1] + b[3] / 2

    entries = [{"at": 0.0, "box": "full"}]
    current = None                                         # box of the active zoom (None: full)
    last_change = -1e9
    for t, box in changes:
        if box is None:
            continue
        if box[2] * box[3] > full_share * width * height:
            if current is not None:
                entries.append({"at": round(t, 2), "box": "full"})
                current = None
            last_change = t
            continue
        if current is not None:
            (cx, cy), (bx, by) = centre(current), centre(box)
            if abs(cx - bx) < near * width and abs(cy - by) < near * height:
                merged = union(current, box)
                if merged[2] * merged[3] <= full_share * width * height:
                    current = merged
                    entries[-1]["box"] = list(current)
                last_change = t
                continue
        if entries[-1]["at"] > t - 0.01 and entries[-1]["box"] != "full":
            entries[-1]["box"] = list(box)
        else:
            entries.append({"at": round(t, 2), "box": list(box)})
        current, last_change = box, t
    return entries


def grey_frames(video, every, scale_w=480):
    import numpy as np
    width, height, _, _ = probe(video)
    h = int(round(height * scale_w / width / 2)) * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps=1/{every},scale={scale_w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, scale_w), width / scale_w


def suggest(a):
    width, height, _, duration = probe(a.video)
    frames, k = grey_frames(a.video, a.every)
    changes = []
    for i in range(1, len(frames)):
        box = change_box(frames[i - 1], frames[i])
        changes.append((i * a.every, None if box is None else tuple(int(v * k) for v in box)))
    entries = plan_zooms(changes, width, height)
    json.dump(entries, open(a.out, "w", encoding="utf-8"), indent=1)
    for e in entries:
        print(f"  {e['at']:7.2f} s  {e['box']}")
    if a.sheet:
        sheet(a.video, entries, a.sheet, width, height)
        print(f"Wrote {a.sheet}: check each box against what happens on screen, then edit {a.out}.")
    print(f"Wrote {a.out}: {len(entries)} entries. Then: screen.py zoom {a.video} {a.out}")


def sheet(video, entries, path, width, height):
    import cv2
    import numpy as np
    tiles = []
    for e in entries[:12]:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{e['at'] + 0.3:.2f}", "-i", video, "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        if len(raw) < width * height * 3:
            continue
        f = np.frombuffer(raw, np.uint8).reshape(height, width, 3).copy()
        if e["box"] != "full":
            x, y, w, h = e["box"]
            cv2.rectangle(f, (x, y), (x + w, y + h), (0, 200, 255), max(3, width // 300))
        cv2.putText(f, f"{e['at']:.1f} s", (20, height // 10), cv2.FONT_HERSHEY_SIMPLEX, height / 500, (0, 0, 255),
                    max(2, width // 500), cv2.LINE_AA)
        tiles.append(cv2.resize(f, (480, int(480 * height / width)), interpolation=cv2.INTER_AREA))
    if tiles:
        while len(tiles) % 3:
            tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(path, np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))


# ---- zoom ----------------------------------------------------------------------------------------------------------

def fit_box(box, width, height, max_zoom=2.5, pad=0.15):
    """The visible area for a box: (left, top, w) with the video's shape, a margin round the box, inside the frame."""
    if box == "full":
        return 0.0, 0.0, float(width)
    x, y, w, h = box
    w, h = w * (1 + 2 * pad), h * (1 + 2 * pad)
    vw = max(w, h * width / height, width / max_zoom)
    vw = min(vw, width)
    vh = vw * height / width
    cx, cy = x + box[2] / 2, y + box[3] / 2
    left = min(max(cx - vw / 2, 0), width - vw)
    top = min(max(cy - vh / 2, 0), height - vh)
    return left, top, vw


def zoom_filter(entries, width, height, move=0.8, max_zoom=2.5):
    """A perspective filter that eases between the visible areas of the entries."""
    views = [(float(e["at"]), fit_box(e["box"], width, height, max_zoom)) for e in entries]
    views.sort(key=lambda v: v[0])
    L0, T0, W0 = views[0][1]
    terms = {"L": [f"{L0:.2f}"], "T": [f"{T0:.2f}"], "W": [f"{W0:.2f}"]}
    prev = views[0][1]
    for i, (t, view) in enumerate(views[1:], 1):
        nxt = views[i + 1][0] if i + 1 < len(views) else None
        d = min(move, (nxt - t) * 0.9) if nxt else move
        p = f"clip((in/FR-{t:.3f})/{d:.3f},0,1)"
        ease = f"(3*pow({p},2)-2*pow({p},3))"
        for key, a, b in zip("LTW", prev, view):
            if abs(b - a) > 0.01:
                terms[key].append(f"{b - a:.2f}*{ease}")
        prev = view
    L, T, W = ("(" + "+".join(terms[k]) + ")" for k in "LTW")
    H = f"({W}*{height / width:.6f})"
    corners = [(L, T), (f"({L}+{W})", T), (L, f"({T}+{H})"), (f"({L}+{W})", f"({T}+{H})")]
    return ":".join(f"x{i}='{x}':y{i}='{y}'" for i, (x, y) in enumerate(corners)), views


def zoom(a):
    width, height, fps, _ = probe(a.video)
    entries = json.load(open(a.zooms, encoding="utf-8"))
    if not entries:
        sys.exit(f"{a.zooms} is empty.")
    args, views = zoom_filter(entries, width, height, a.move, a.max_zoom)
    line = f"perspective={args.replace('FR', f'{fps:.6f}')}:interpolation=cubic:eval=frame"
    open(a.out, "w", encoding="utf-8").write(line + "\n")
    for t, (left, top, w) in views:
        print(f"  {t:7.2f} s  zoom {width / w:.2f}x at {left:.0f},{top:.0f}")
    print(f"Wrote {a.out}. Render: ffmpeg -i {a.video} -/filter_complex {a.out} ... (FFmpeg 6: -filter_complex_script)")


# ---- stack ---------------------------------------------------------------------------------------------------------

def face_x(video, model, width, height):
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions
    small_w = 640
    small_h = int(round(height * small_w / width / 2)) * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps=1,scale={small_w}:{small_h}",
                          "-frames:v", "20", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, small_h, small_w, 3)
    xs = []
    with FaceLandmarker.create_from_options(FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model),
                                                                  num_faces=1)) as lm:
        for f in frames:
            found = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f))).face_landmarks
            if found:
                xs.append((found[0][33].x + found[0][263].x) / 2 * width)
    return float(np.median(xs)) if xs else None


def panel_crop(width, height, panel_w, panel_h, centre_x=None):
    """The largest crop with the panel's shape, centred on centre_x (or the middle), inside the frame: (w, h, x, y)."""
    if width / height > panel_w / panel_h:
        h = height
        w = int(round(h * panel_w / panel_h / 2)) * 2
    else:
        w = width
        h = int(round(w * panel_h / panel_w / 2)) * 2
    cx = width / 2 if centre_x is None else centre_x
    x = int(min(max(cx - w / 2, 0), width - w))
    return w, h, x, (height - h) // 2


def stack_graph(screen_size, camera_size, out_w, out_h, split, centre_x, audio):
    top_h = int(round(out_h * split / 2)) * 2
    bottom_h = out_h - top_h
    sw, sh, sx, sy = panel_crop(*screen_size, out_w, top_h)
    cw, ch, cx, cy = panel_crop(*camera_size, out_w, bottom_h, centre_x)
    a = "0:a" if audio == "screen" else "1:a"
    return (f"[0:v]crop={sw}:{sh}:{sx}:{sy},scale={out_w}:{top_h}:flags=lanczos,setsar=1[top];\n"
            f"[1:v]crop={cw}:{ch}:{cx}:{cy},scale={out_w}:{bottom_h}:flags=lanczos,setsar=1[bottom];\n"
            f"[top][bottom]vstack=inputs=2,format=yuv420p[v];\n"
            f"[{a}]anull[a]\n")


def stack(a):
    out_w, out_h = (int(v) for v in a.size.lower().split("x"))
    sw, sh, _, sd = probe(a.screen)
    cw, ch, _, cd = probe(a.camera)
    if abs(sd - cd) > 0.5:
        print(f"Note: the screen recording lasts {sd:.1f} s and the camera {cd:.1f} s. Cut them to the same moment "
              "first, or the speaker won't match the screen.")
    centre = a.face_x
    if centre is None and a.face_model:
        centre = face_x(a.camera, a.face_model, cw, ch)
        print("Face found at x =", "not found (using the middle)" if centre is None else f"{centre:.0f}")
    graph = stack_graph((sw, sh), (cw, ch), out_w, out_h, a.split, centre, a.audio)
    open(a.out, "w", encoding="utf-8").write(graph)
    print(f'Wrote {a.out}. Render: ffmpeg -i {a.screen} -i {a.camera} -/filter_complex {a.out} -map "[v]" -map "[a]" '
          "... (FFmpeg 6: -filter_complex_script). Captions and graphics for the vertical size go on top.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suggest")
    s.add_argument("video")
    s.add_argument("--every", type=float, default=0.5)
    s.add_argument("--out", default="zooms.json")
    s.add_argument("--sheet", default="zooms.png")
    z = sub.add_parser("zoom")
    z.add_argument("video")
    z.add_argument("zooms")
    z.add_argument("--move", type=float, default=0.8)
    z.add_argument("--max-zoom", type=float, default=2.5)
    z.add_argument("--out", default="zoom.txt")
    k = sub.add_parser("stack")
    k.add_argument("screen")
    k.add_argument("camera")
    k.add_argument("--face-model")
    k.add_argument("--face-x", type=float)
    k.add_argument("--size", default="1080x1920")
    k.add_argument("--split", type=float, default=0.5)
    k.add_argument("--audio", choices=["camera", "screen"], default="camera")
    k.add_argument("--out", default="stack.txt")
    a = ap.parse_args()
    {"suggest": suggest, "zoom": zoom, "stack": stack}[a.cmd](a)


if __name__ == "__main__":
    main()
