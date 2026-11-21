"""Pixelates the faces of other people in a video and leaves the speaker's face alone.

Three steps, each on the same picture (the render the other masks are built on, normally clean.mp4):

  <face python> -I pixelfaces.py scan   clean.mp4 <face_landmarker.task> [--every 1] [--thorough]
      Finds every face in every frame (in the whole frame and in overlapping squares, because the detector
      misses faces that are under a tenth of the frame; --thorough also tries half-size squares, for faces of
      about 50 px), follows each one, and decides who the speaker is (the face
      seen most). Writes pixelfaces.json and pixelfaces/sheet.png: sample frames with every face
      marked, green = stays sharp, red = pixelated, each with its track number. Prints each track
      and the stretches where the detector lost a face and the box was carried over.
  python -I pixelfaces.py build clean.mp4
      Reads pixelfaces.json and retouch.json (pixel_* settings) and writes pixmask.mkv: white
      where the picture is pixelated. Quick, so margin, block or pixel_keep can be changed and
      rebuilt without scanning again. Needs no OpenCV. Prints the FFmpeg command that applies it.
  <face python> -I pixelfaces.py verify pixelated.mp4 <face_landmarker.task>
      Looks for faces in the result: any face found outside the speaker's box is a leak, listed
      with its time. Run it, and look at the sheet, before the video goes out.

Why alphamerge and overlay, not maskedmerge: maskedmerge squeezes a gray mask into video levels (0 becomes
16, 255 becomes 235), so in a test 11,644 of 32,000 pixels of a pixelated face still had some of the
original in them. Alpha is exact: inside the mask the result equals the pixelated picture, outside it equals
the source.

Why a mask and not a blur: pixelated squares can't be undone and the squares sit on a grid, so the
box is snapped outwards to whole squares. Pixelate before graphics, zooms and captions: later steps
must see the pixelated picture, so a punch-in or a cover frame never shows the original.

What it cannot do: a detector misses faces that are small, in profile, turned away, or under a
mask, so look at the sheet and the gap list, add what is missing with pixel_extra, and run verify.
It hides faces only: voices and name tags stay. A face a frame cut in half by the edge is the
detector's blind spot too: add it with pixel_extra.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402

TRACKS = "pixelfaces.json"
MASK = "pixmask.mkv"


# ---------------------------------------------------------------- tracking (numpy only)

def _center(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def _size(b):
    return max(b[2] - b[0], b[3] - b[1], 1)


def build_tracks(frames, max_lost, min_frames=4):
    """frames: for every video frame, a list of face boxes [x0, y0, x1, y1] (empty if none).
    Follows each face from frame to frame; a face lost for up to max_lost frames can come back.
    Returns [{"id": n, "boxes": {frame: box}}]; tracks seen in fewer than min_frames frames
    are dropped (they are false detections), and ids are never reused."""
    tracks = []
    for n, boxes in enumerate(frames):
        pairs = []
        for i, b in enumerate(boxes):
            for t in tracks:
                last_frame, last_box = t["last"]
                lost = n - last_frame
                if lost > max_lost:
                    continue
                cx, cy = _center(b)
                lx, ly = _center(last_box)
                d = float(np.hypot(cx - lx, cy - ly)) / max(_size(b), _size(last_box))
                if d < min(0.8 + 0.05 * lost, 3.0):
                    pairs.append((d, i, t["id"]))
        pairs.sort()
        used_box, used_track = set(), set()
        for d, i, tid in pairs:
            if i in used_box or tid in used_track:
                continue
            used_box.add(i)
            used_track.add(tid)
            tracks[tid]["boxes"][n] = list(boxes[i])
            tracks[tid]["last"] = (n, boxes[i])
        for i, b in enumerate(boxes):
            if i not in used_box:
                tracks.append({"id": len(tracks), "boxes": {n: list(b)}, "last": (n, b)})
    return [{"id": t["id"], "boxes": t["boxes"]} for t in tracks if len(t["boxes"]) >= min_frames]


def pick_speaker(tracks):
    """The track with the most face area over time (the person who is in the picture most), or None."""
    best, best_area = None, 0.0
    for t in tracks:
        area = sum((b[2] - b[0]) * (b[3] - b[1]) for b in t["boxes"].values())
        if area > best_area:
            best, best_area = t["id"], area
    return best


def fill_track(boxes, n_frames, gap, hold):
    """{frame: box} -> array (n_frames, 4), NaN where the track is not on screen. Misses of up to
    `gap` frames are bridged by moving the box between the sightings; the box is held `hold` frames
    before the first and after the last sighting."""
    out = np.full((n_frames, 4), np.nan)
    frames = sorted(int(k) for k in boxes)
    for k in frames:
        out[k] = boxes[k] if k in boxes else boxes[str(k)]
    for a, b in zip(frames, frames[1:]):
        if 1 < b - a <= gap + 1:
            for k in range(a + 1, b):
                w = (k - a) / (b - a)
                out[k] = (1 - w) * out[a] + w * out[b]
    for k in range(max(0, frames[0] - hold), frames[0]):
        out[k] = out[frames[0]]
    for k in range(frames[-1] + 1, min(n_frames, frames[-1] + hold + 1)):
        out[k] = out[frames[-1]]
    return out


def envelope(arr, radius=2):
    """Each box becomes the union of the boxes within `radius` frames: the box never lags behind a
    face that moves, and it doesn't jitter."""
    out = arr.copy()
    for n in range(len(arr)):
        if np.isnan(arr[n, 0]):
            continue
        window = arr[max(0, n - radius):n + radius + 1]
        window = window[~np.isnan(window[:, 0])]
        out[n] = [window[:, 0].min(), window[:, 1].min(), window[:, 2].max(), window[:, 3].max()]
    return out


def grow(box, margin, width, height):
    w, h = box[2] - box[0], box[3] - box[1]
    return [max(0.0, box[0] - w * margin), max(0.0, box[1] - h * (margin + 0.15)),
            min(float(width), box[2] + w * margin), min(float(height), box[3] + h * margin)]


def frame_boxes(track_list, n_frames, width, height, fps, cfg, only=None):
    """For every frame, the boxes to cover: [[x0, y0, x1, y1], ...] with the margin added.
    `only` is a set of track ids (default: every track but the ones kept sharp are chosen by the caller)."""
    gap = max(1, round(cfg["pixel_gap"] * fps))
    hold = max(0, round(cfg["pixel_hold"] * fps))
    result = [[] for _ in range(n_frames)]
    for t in track_list:
        if only is not None and t["id"] not in only:
            continue
        arr = envelope(fill_track(t["boxes"], n_frames, gap, hold))
        for n in range(n_frames):
            if not np.isnan(arr[n, 0]):
                result[n].append(grow(arr[n], cfg["pixel_margin"], width, height))
    return result


def add_extras(boxes, extras, fps, width, height):
    for e in extras:
        x, y, w, h = e["box"]
        for n in range(max(0, round(e["start"] * fps)), min(len(boxes), round(e["end"] * fps) + 1)):
            boxes[n].append([max(0.0, x), max(0.0, y), min(float(width), x + w), min(float(height), y + h)])


def choose_block(all_boxes, cfg):
    if cfg["pixel_block"]:
        return int(cfg["pixel_block"])
    widest = max((b[2] - b[0] for frame in all_boxes for b in frame), default=0)
    return max(12, int(round(widest / 7 / 2)) * 2)


def mask_frame(boxes, width, height, block):
    """A gray frame, 255 inside the boxes, each box snapped outwards to whole squares so no square
    is half pixelated and half sharp."""
    m = np.zeros((height, width), np.uint8)
    for x0, y0, x1, y1 in boxes:
        a, b = int(x0 // block * block), int(y0 // block * block)
        c, d = int(-(-x1 // block) * block), int(-(-y1 // block) * block)
        m[max(0, b):min(height, d), max(0, a):min(width, c)] = 255
    return m


def runs(frames):
    """[3, 4, 5, 9] -> [(3, 5), (9, 9)]"""
    out = []
    for n in sorted(frames):
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


# source pixel format -> (the same with an alpha plane, the format name overlay uses)
ALPHA = {"yuv420p": ("yuva420p", "yuv420"), "yuv422p": ("yuva422p", "yuv422"), "yuv444p": ("yuva444p", "yuv444"),
         "yuv420p10le": ("yuva420p10le", "yuv420p10"), "yuv422p10le": ("yuva422p10le", "yuv422p10"),
         "yuv444p10le": ("yuva444p10le", "yuv444p10")}


def source_format(video):
    """The video's pixel format, so a 10-bit (Log) render stays 10-bit; yuv420p if it can't be read."""
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt",
                              "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip()
    except OSError:
        out = ""
    return out if out in ALPHA else "yuv420p"


def pixelate_graph(block, pix_fmt):
    with_alpha, overlay_format = ALPHA[pix_fmt]
    return (f"[0:v]split[s0][s1];[s1]pixelize=w={block}:h={block},format={with_alpha}[p];[1:v]format=gray[m];"
            f"[p][m]alphamerge[pm];[s0][pm]overlay=format={overlay_format}[v]")


def tiles(width, height, thorough=False):
    """Squares (x, y, side) to search besides the whole frame. The face detector looks at a small copy of
    what it is given, so a face that is under about a tenth of the frame is missed: on a real 1280x720
    frame a face 125 px wide was not found in the whole frame and was found in a 720 px square. The squares
    overlap by half, so a face cut by one square's edge is whole in the next. `thorough` adds squares of half
    the size, for faces about 50 px wide (many more squares, so slower)."""
    short = min(width, height)
    sides = [short] + ([short // 2] if thorough else [])
    out = []
    for side in sides:
        step = max(1, side // 2)
        xs = list(range(0, max(1, width - side + 1), step))
        ys = list(range(0, max(1, height - side + 1), step))
        if xs[-1] + side < width:
            xs.append(width - side)
        if ys[-1] + side < height:
            ys.append(height - side)
        out += [(x, y, side) for y in ys for x in xs]
    return out


def merge_boxes(boxes):
    """The same face found in the whole frame and in a square (or two) is kept once: the largest box
    first, a smaller one is dropped when its centre lies inside one already kept."""
    kept = []
    for b in sorted(boxes, key=lambda b: -(b[2] - b[0]) * (b[3] - b[1])):
        cx, cy = _center(b)
        if not any(k[0] <= cx <= k[2] and k[1] <= cy <= k[3] for k in kept):
            kept.append(list(b))
    return kept


def stamp(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


# ---------------------------------------------------------------- detection (needs OpenCV and mediapipe)

def detect_all(video, model, faces, every, thorough=False):
    """Every face in every frame: ([boxes per frame], width, height, fps). Looks in the whole frame and in
    overlapping squares (see tiles), because small faces are missed otherwise."""
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

    capture = cv2.VideoCapture(video)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    options = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model),
                                    running_mode=RunningMode.IMAGE, num_faces=faces)
    areas = [(0, 0, width, height)] + [(x, y, s) for x, y, s in tiles(width, height, thorough)]
    areas = [(a[0], a[1], a[2], a[3]) if len(a) == 4 else (a[0], a[1], a[2], a[2]) for a in areas]
    frames = []
    with FaceLandmarker.create_from_options(options) as landmarker:
        n = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            found = []
            if n % every == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                for x, y, w, h in areas:
                    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb[y:y + h, x:x + w]))
                    for points in landmarker.detect(image).face_landmarks:
                        xs = [x + p.x * w for p in points]
                        ys = [y + p.y * h for p in points]
                        found.append([min(xs), min(ys), max(xs), max(ys)])
                found = merge_boxes(found)
            frames.append(found)
            n += 1
    capture.release()
    return frames, width, height, fps


def sheet(video, shown, width, height, fps, speakers, path):
    """Sample frames with the boxes drawn: green stays sharp, red is pixelated."""
    import cv2

    capture = cv2.VideoCapture(video)
    total = len(shown)
    with_faces = [n for n in range(total) if shown[n]]
    picks = sorted({with_faces[int(i * (len(with_faces) - 1) / 11)] for i in range(12)}) if with_faces else \
        [int(i * max(total - 1, 0) / 11) for i in range(12)]
    tiles = []
    for n in picks:
        capture.set(cv2.CAP_PROP_POS_FRAMES, n)
        ok, frame = capture.read()
        if not ok:
            continue
        for tid, box in shown[n]:
            colour = (0, 200, 0) if tid in speakers else (0, 0, 255)
            cv2.rectangle(frame, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), colour, max(3, width // 300))
            cv2.putText(frame, str(tid), (int(box[0]) + 6, int(box[1]) + max(30, width // 40)),
                        cv2.FONT_HERSHEY_SIMPLEX, max(1.0, width / 900), colour, 3)
        small = cv2.resize(frame, (360, int(360 * height / width)))
        cv2.putText(small, stamp(n / fps), (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        tiles.append(small)
    capture.release()
    if not tiles:
        return
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    cv2.imwrite(path, np.vstack(rows))


# ---------------------------------------------------------------- the three commands

def keep_ids(data, cfg):
    if cfg["pixel_keep"] is not None:
        return set(cfg["pixel_keep"])
    return {data["speaker"]} if data["speaker"] is not None else set()


def scan(a):
    cfg = settings.load()
    frames, width, height, fps = detect_all(a.video, a.model, cfg["pixel_faces"], a.every, a.thorough)
    tracks = build_tracks(frames, max_lost=max(1, round(cfg["pixel_gap"] * fps)))
    speaker = pick_speaker(tracks)
    data = {"video": os.path.basename(a.video), "width": width, "height": height, "fps": fps, "frames": len(frames),
            "speaker": speaker, "tracks": [{"id": t["id"], "boxes": t["boxes"]} for t in tracks]}
    with open(TRACKS, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"{len(frames)} frames, {len(tracks)} faces followed. Speaker (stays sharp): track {speaker}.")
    mean = {t["id"]: np.mean([b[2] - b[0] for b in t["boxes"].values()]) for t in tracks}
    for t in tracks:
        seen = sorted(t["boxes"])
        role = "SPEAKER, sharp" if t["id"] in keep_ids(data, cfg) else "pixelated"
        note = ""
        if speaker is not None and t["id"] != speaker and mean[t["id"]] >= 0.7 * mean[speaker]:
            note = "  <- as big as the speaker: check it isn't the speaker (then pixel_keep)"
        print(f"  track {t['id']}: {stamp(seen[0] / fps)} to {stamp(seen[-1] / fps)}, seen in {len(seen)} frames, "
              f"{mean[t['id']]:.0f} px wide: {role}{note}")
    gap = max(1, round(cfg["pixel_gap"] * fps))
    for t in tracks:
        missing = [n for n in range(min(t["boxes"]), max(t["boxes"]) + 1) if n not in t["boxes"]]
        for first, last in runs(missing):
            kind = "carried over" if last - first + 1 <= gap else "NOT covered (too long)"
            print(f"  track {t['id']}: lost {stamp(first / fps)} to {stamp(last / fps)}, {kind}: look at this part")
    kept = keep_ids(data, cfg)
    shown = [[] for _ in range(len(frames))]
    for t in tracks:
        for n, row in enumerate(frame_boxes([t], len(frames), width, height, fps, cfg)):
            shown[n] += [(t["id"], b) for b in row]
    sheet(a.video, shown, width, height, fps, kept, os.path.join("pixelfaces", "sheet.png"))
    print("Look at pixelfaces/sheet.png: green stays sharp, red is pixelated. Then run build.")


def build(a):
    cfg = settings.load()
    with open(TRACKS, encoding="utf-8") as f:
        data = json.load(f)
    width, height, fps, n = data["width"], data["height"], data["fps"], data["frames"]
    kept = keep_ids(data, cfg)
    tracks = [{"id": t["id"], "boxes": {int(k): v for k, v in t["boxes"].items()}} for t in data["tracks"]]
    boxes = frame_boxes(tracks, n, width, height, fps, cfg, only={t["id"] for t in tracks} - kept)
    add_extras(boxes, cfg["pixel_extra"], fps, width, height)
    if not any(boxes):
        print("Nobody to pixelate: no mask written.")
        return
    block = choose_block(boxes, cfg)
    writer = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{width}x{height}",
                               "-r", f"{fps}", "-i", "-", "-c:v", "ffv1", MASK], stdin=subprocess.PIPE)
    for frame in boxes:
        writer.stdin.write(mask_frame(frame, width, height, block).tobytes())
    writer.stdin.close()
    if writer.wait():
        sys.exit("ffmpeg could not write the mask.")
    covered = sum(1 for frame in boxes if frame)
    print(f"Wrote {MASK}: {covered} of {n} frames have a pixelated area, squares of {block} px.")
    print(f'Apply it: ffmpeg -i {a.video} -i {MASK} -filter_complex "{pixelate_graph(block, source_format(a.video))}" '
          '-map "[v]" -map 0:a? -c:a copy <in-between encoder> pixelated.mp4')
    print("Then run verify on pixelated.mp4. Do this before graphics, zooms and captions.")


def verify(a):
    cfg = settings.load()
    with open(TRACKS, encoding="utf-8") as f:
        data = json.load(f)
    frames, width, height, fps = detect_all(a.video, a.model, cfg["pixel_faces"], a.every, thorough=True)
    kept = keep_ids(data, cfg)
    tracks = [{"id": t["id"], "boxes": {int(k): v for k, v in t["boxes"].items()}} for t in data["tracks"] if t["id"] in kept]
    safe = frame_boxes(tracks, len(frames), width, height, fps, cfg)
    leaks = []
    for n, found in enumerate(frames):
        for b in found:
            cx, cy = _center(b)
            if not any(s[0] <= cx <= s[2] and s[1] <= cy <= s[3] for s in safe[n] if n < len(safe)):
                leaks.append(n)
                break
    if not leaks:
        print("No face found outside the speaker's box. (The detector's blind spots are still blind: look at the video.)")
        return
    for first, last in runs(leaks):
        print(f"A face is visible from {stamp(first / fps)} to {stamp(last / fps)}.")
    print("Add these with pixel_extra, or check pixel_keep, then build and apply again.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("scan")
    s.add_argument("video")
    s.add_argument("model")
    s.add_argument("--every", type=int, default=1, help="look at every Nth frame (2 is faster; gaps are bridged)")
    s.add_argument("--thorough", action="store_true", help="also search squares half the size: faces of about 50 px, much slower")
    b = sub.add_parser("build")
    b.add_argument("video", nargs="?", default="clean.mp4")
    v = sub.add_parser("verify")
    v.add_argument("video")
    v.add_argument("model")
    v.add_argument("--every", type=int, default=2, help="look at every Nth frame (default 2); always the thorough search")
    a = ap.parse_args()
    {"scan": scan, "build": build, "verify": verify}[a.command](a)


if __name__ == "__main__":
    main()
