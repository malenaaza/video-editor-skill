"""Reframes a wide (16:9) video to vertical (9:16) for Shorts, Reels and TikTok, following the speaker like a camera
operator would.

  <face python> -I reframe.py <wide video> <face_landmarker.task> [--size 1080x1920] [--band 0.12]
                [--patience 0.4] [--move 0.6] [--every 0.2] [--check reframe.png] [--out reframe.txt]

The crop is as tall as the frame and 9/16 as wide (from 4K, 1216x2160, scaled to 1080x1920; from 1080p it would be
608x1080 blown up, which looks soft: film 4K when the video will also be cut into Shorts). It finds the face every
--every seconds (MediaPipe face landmarks, with the EdgeFace fallback for a face cut by the frame edge) and plans the
crop like a person holding the camera:
  - it holds perfectly still while the face stays inside a band around the middle of the crop (--band, a share of the
    crop width on each side), so small head movements while talking don't move the picture;
  - when the face stays outside the band for --patience seconds (not a quick lean or gesture), it moves to put the face
    back in the middle, easing in and out over --move seconds; a face about to leave the picture (beyond 30% of the
    crop width from the middle) is followed at once, and a moving speaker is aimed ahead, where they'll be when the
    move ends, so a walk across the room is a chain of moves that keeps up;
  - when the face jumps by more than a third of the crop width from one look to the next (a cut to another framing),
    it cuts too, instead of panning across the room.
Still holds and short eased moves also keep FFmpeg's whole-pixel crop from showing as a shake: a slow, constant pan
would.

Stretches with no face (a screen recording, the face turned away or covered) keep the last position, or the middle
at the start, and are listed: a screen recording usually needs its own vertical layout instead (screen.py stack).

It writes reframe.txt, one filter line (crop, then scale) to put first in the vertical render's picture chain, on the
retouched wide video. Make the vertical version's captions and graphics for the vertical size afterwards, on top: the
wide version's captions would be cut off. --check writes frames of the wide video with the crop drawn on them: look
at it. Prints the moves, the cuts and the stretches without a face. Needs OpenCV, MediaPipe and FFmpeg for the
tracking; the planning itself is plain Python.
"""
import argparse
import json
import os
import subprocess
import sys
from fractions import Fraction

sys.stdout.reconfigure(encoding="utf-8")


def crop_width(height):
    """9:16 of the height, rounded to an even number of pixels (the chroma planes need it)."""
    return int(round(height * 9 / 16 / 2)) * 2


def plan_path(samples, width, crop_w, band=0.12, patience=0.4, move=0.6, jump=1 / 3):
    """Where the crop's centre goes. samples: [(time, face x in pixels or None)], in time order.

    Returns (start, moves, gaps): the first centre; moves as (start time, end time, from x, to x), where start == end
    is a cut; gaps as (start, end) stretches with no face. Moves never overlap."""
    half = crop_w / 2
    lo, hi = half, width - half

    def clamp(x):
        return min(max(x, lo), hi)

    faces = [(t, x) for t, x in samples if x is not None]
    centre = clamp(faces[0][1]) if faces else width / 2
    start, moves, gaps = centre, [], []
    busy_until, outside_since, last_x, last_t, gap_start, last_speed = -1.0, None, None, None, None, 0.0
    for t, x in samples:
        if x is None:
            if gap_start is None:
                gap_start = t
            outside_since = None
            continue
        if gap_start is not None:
            gaps.append((gap_start, t))
            gap_start = None
        jumped = last_x is not None and abs(x - last_x) > jump * crop_w
        speed = 0.0 if last_x is None or jumped or t <= last_t else (x - last_x) / (t - last_t)
        # walking: two steps in a row the same way, each faster than 15% of the crop width a second (a quick lean
        # out and back is one step, then one back, so it doesn't count)
        fast = 0.15 * crop_w
        moving = abs(speed) > fast and abs(last_speed) > fast and speed * last_speed > 0
        lead = (speed + last_speed) / 2 * move if moving else 0.0
        last_x, last_t, last_speed = x, t, speed
        if t < busy_until:
            continue
        if jumped:                                             # a cut in the footage: cut with it
            if abs(clamp(x) - centre) >= 1:
                moves.append((t, t, centre, clamp(x)))
                centre = clamp(x)
            outside_since = None
            continue
        target = clamp(x + lead)                               # a walking speaker: aim where they'll be
        urgent = moving or abs(x - centre) > 0.3 * crop_w      # or about to leave the picture: don't wait
        if abs(target - centre) < 1:
            outside_since = None
            continue
        if abs(x - centre) <= band * crop_w:
            outside_since = None
            continue
        if outside_since is None:
            outside_since = t
        if urgent or t - outside_since + 1e-9 >= patience:
            moves.append((t, t + move, centre, target))
            centre, busy_until, outside_since = target, t + move, None
    if gap_start is not None:
        gaps.append((gap_start, samples[-1][0]))
    return start, moves, gaps


def centre_at(t, start, moves):
    """The crop's centre at time t, the same curve the filter draws (for checks)."""
    c = start
    for s, e, a, b in moves:
        if e <= s:
            c += (b - a) * (t >= s)
        else:
            p = min(max((t - s) / (e - s), 0.0), 1.0)
            c += (b - a) * (3 * p * p - 2 * p ** 3)
    return c


def x_expression(start, moves, crop_w):
    """The crop's left edge as an FFmpeg expression of t: still holds, eased moves and cuts, added up."""
    terms = [f"{start - crop_w / 2:.2f}"]
    for s, e, a, b in moves:
        d = b - a
        if e <= s:
            terms.append(f"{d:.2f}*gte(t,{s:.3f})")
        else:
            p = f"clip((t-{s:.3f})/{e - s:.3f},0,1)"
            terms.append(f"{d:.2f}*(3*pow({p},2)-2*pow({p},3))")
    return "+".join(terms)


def filter_line(height, crop_w, start, moves, out_w=1080, out_h=1920):
    x = x_expression(start, moves, crop_w)
    return (f"crop=w={crop_w}:h={height}:x='{x}':y=0,"
            f"scale={out_w}:{out_h}:flags=lanczos,setsar=1")


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", video],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"Can't read {video}: {out.stderr.strip()}")
    info = json.loads(out.stdout)
    s = info["streams"][0]
    return s["width"], s["height"], float(Fraction(s["r_frame_rate"])), float(info["format"]["duration"])


def track(video, model, width, height, every):
    """[(time, face centre x in full-size pixels or None)], one look every `every` seconds."""
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "retouch"))
    from facetrack import EdgeFace

    small_w = 960
    small_h = int(round(height * small_w / width / 2)) * 2
    scale = width / small_w
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps=1/{every},scale={small_w}:{small_h}",
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    options = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model), running_mode=RunningMode.VIDEO,
                                    num_faces=1)
    edge = EdgeFace(model)
    samples, i = [], 0
    with FaceLandmarker.create_from_options(options) as lm:
        while True:
            raw = proc.stdout.read(small_w * small_h * 3)
            if len(raw) < small_w * small_h * 3:
                break
            rgb = np.frombuffer(raw, np.uint8).reshape(small_h, small_w, 3)
            t = i * every
            found = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(t * 1000)).face_landmarks
            x = None
            if found:
                x = (found[0][33].x + found[0][263].x) / 2 * small_w * scale
            else:
                points = edge.detect(np.ascontiguousarray(rgb[:, :, ::-1]))
                if points is not None:
                    x = (points[33][0] + points[263][0]) / 2 * scale
            samples.append((t, x))
            i += 1
    proc.wait()
    edge.close()
    return samples


def check_sheet(video, path, width, height, crop_w, start, moves, duration):
    import cv2
    import numpy as np
    tiles = []
    for k in range(6):
        t = duration * (k + 0.5) / 6
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        if len(raw) < width * height * 3:
            continue
        frame = np.frombuffer(raw, np.uint8).reshape(height, width, 3).copy()
        x0 = int(centre_at(t, start, moves) - crop_w / 2)
        shade = frame.copy()
        shade[:, :x0] //= 3
        shade[:, x0 + crop_w:] //= 3
        cv2.rectangle(shade, (x0, 0), (x0 + crop_w - 1, height - 1), (0, 255, 255), max(2, width // 400))
        cv2.putText(shade, f"{t:.1f} s", (20, height // 12), cv2.FONT_HERSHEY_SIMPLEX, height / 600, (255, 255, 255),
                    max(2, width // 600), cv2.LINE_AA)
        tiles.append(cv2.resize(shade, (640, int(640 * height / width)), interpolation=cv2.INTER_AREA))
    if tiles:
        while len(tiles) % 3:
            tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(path, np.vstack([np.hstack(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("face_model")
    ap.add_argument("--size", default="1080x1920", help="size of the vertical video")
    ap.add_argument("--band", type=float, default=0.12, help="how far the face may drift from the middle, as a share "
                    "of the crop width, before the crop follows")
    ap.add_argument("--patience", type=float, default=0.4, help="seconds the face must stay off-centre before a move")
    ap.add_argument("--move", type=float, default=0.6, help="seconds a move takes")
    ap.add_argument("--every", type=float, default=0.2, help="seconds between looks for the face")
    ap.add_argument("--check", help="write frames with the crop drawn on them to this image")
    ap.add_argument("--out", default="reframe.txt")
    a = ap.parse_args()

    out_w, out_h = (int(v) for v in a.size.lower().split("x"))
    width, height, fps, duration = probe(a.video)
    if width <= height:
        sys.exit(f"{a.video} is {width}x{height}: it's already vertical, nothing to reframe.")
    crop_w = crop_width(height)
    if height < out_h:
        print(f"Note: the crop is {crop_w}x{height}, enlarged to {out_w}x{out_h}, so it will look softer than the wide "
              "version. Filming in 4K avoids this.")
    samples = track(a.video, a.face_model, width, height, a.every)
    found = sum(x is not None for _, x in samples)
    if not found:
        sys.exit("No face found anywhere in the video: reframe it by hand, or use a stacked layout.")
    start, moves, gaps = plan_path(samples, width, crop_w, a.band, a.patience, a.move)
    open(a.out, "w", encoding="utf-8").write(filter_line(height, crop_w, start, moves, out_w, out_h) + "\n")
    cuts = sum(1 for s, e, _, _ in moves if e <= s)
    print(f"Face found in {found} of {len(samples)} looks. Crop {crop_w}x{height} -> {out_w}x{out_h}: "
          f"{len(moves) - cuts} eased move(s), {cuts} cut(s).")
    for s, e, a_, b in moves:
        print(f"  {s:7.2f} s  {'cut ' if e <= s else 'move'}  {a_ - crop_w / 2:6.0f} -> {b - crop_w / 2:6.0f} px")
    long_gaps = [(s, e) for s, e in gaps if e - s >= 1.0]
    for s, e in long_gaps:
        print(f"  No face from {s:.1f} to {e:.1f} s: the crop holds still there. If it's a screen recording, give "
              "that part its own vertical layout (screen above, face below).")
    if a.check:
        check_sheet(a.video, a.check, width, height, crop_w, start, moves, duration)
        print(f"Wrote {a.check}: look at it.")
    print(f"Wrote {a.out}. Put its line first in the vertical render's picture chain; captions and graphics for "
          "the vertical size go on top.")


if __name__ == "__main__":
    main()
