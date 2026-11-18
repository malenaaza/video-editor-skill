"""A slow push in on the speaker's face at a key moment, like a camera moving closer, and back out.

  <face python> -I pushin.py <video> <face_landmarker.task> --at 12.4 [--until 16.0]
                [--zoom 1.15] [--duration 1.5] [--back 0.4] [--caption-top 1320]
  <face python> -I pushin.py <video> <face_landmarker.task> --say "el secreto" [--until-say "funciona"]

<video> is the footage the push goes on (retouched.mp4: times are in the finished video, like captions.json).
--say finds a phrase in captions.json (accents and case ignored); without --until or --until-say the push lasts to the
end of that caption. It prints the times: check them with the user.

It finds the face on the frame where the push starts (MediaPipe face landmarks, with the EdgeFace fallback for a face
cut by the frame edge) and moves towards it: the face stays where it is on screen and grows, so it feels like a camera
moving in, not a jump. The zoom eases in over --duration seconds, holds, and eases back out over the last --back
seconds of the part (--back 0 cuts back to the full frame at the end, best on a new sentence).

Like the punch-in zooms (Rule 10), it never cuts off the head: at full zoom the top of the head (forehead landmark 10
minus 0.45 face heights) stays at least 60 px below the top of the frame, and with --caption-top the chin stays above
the caption area. In a close-up where the head is already cut by the top of the frame, it keeps the forehead in view
instead (60 px of room above landmark 10); where the chin is already under the captions, it keeps the mouth above them.
It moves the aim up or down to make room, then lowers the zoom (down to 1.04), and says so; if even that doesn't fit,
it says to skip the push.

It writes pushin.txt, one filter line for the picture chain. Put it first in the text-and-graphics render, on
retouched.mp4 (never in clean.mp4: the masks are built on that), so titles, captions and graphics don't zoom. The
zoom is drawn with sub-pixel precision (FFmpeg's perspective filter): zoompan and crop move in whole pixels, and on a
slow zoom that shows as a shake. Needs OpenCV, MediaPipe and FFmpeg.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unicodedata
from fractions import Fraction

sys.stdout.reconfigure(encoding="utf-8")

HEAD_ROOM = 60  # pixels kept above the top of the head at full zoom
MIN_ZOOM = 1.04


def words_of(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return ["".join(c for c in w if c.isalnum()) for w in text.split() if any(c.isalnum() for c in w)]


def find(flat, phrase, after=-1.0):
    want = words_of(phrase)
    for i in range(len(flat) - len(want) + 1):
        if want and flat[i][0] > after and [w[2] for w in flat[i:i + len(want)]] == want:
            return i, i + len(want) - 1
    return None


def times_from_captions(path, say, until_say):
    flat = []  # (start, end, word, caption end)
    for c in json.load(open(path, encoding="utf-8")):
        for s, e, text in c["words"]:
            flat += [(s, e, w, c["end"]) for w in words_of(text)]
    hit = find(flat, say)
    if not hit:
        sys.exit(f'"{say}" is not in {path}.')
    start = flat[hit[0]][0]
    if until_say:
        end_hit = find(flat, until_say, after=start)
        if not end_hit:
            sys.exit(f'"{until_say}" is not said after "{say}" in {path}.')
        return start, flat[end_hit[1]][1]
    return start, flat[hit[1]][3]


def aim(face, width, height, zoom, caption_top=None):
    """The crop at full zoom: (zoom, x0, y0, notes). face: centre_x, centre_y, head_top, forehead, chin, mouth (pixels).

    The crop is width/zoom x height/zoom. Moving in on the face's centre keeps the face where it is on screen; the
    crop is moved up or down only as much as the head room and the caption area need, and the zoom is lowered when
    no position works. Returns zoom None when even MIN_ZOOM doesn't fit."""
    notes = []
    top, top_name = face["head_top"], "the head in the frame"
    if top < HEAD_ROOM:  # a close-up: the head is already cut by the frame's top
        top, top_name = face["forehead"], "the forehead in view"
        notes.append("close-up: the top of the head is already out of the frame, so the push keeps the forehead in view")
    bottom, bottom_name = face["chin"], "the chin above the captions"
    if caption_top is not None and face["chin"] > caption_top:
        bottom, bottom_name = face["mouth"], "the mouth above the captions"
        notes.append("the chin is already under the caption area, so the push keeps the mouth above it")
    z = zoom
    while z >= MIN_ZOOM - 1e-9:
        w, h = width / z, height / z
        x0 = min(max(face["centre_x"] * (1 - 1 / z), 0), width - w)
        want_y = face["centre_y"] * (1 - 1 / z)
        low = 0.0 if caption_top is None else bottom - caption_top / z   # chin (or mouth) above the caption area
        high = top - HEAD_ROOM / z                                          # room above the head (or forehead)
        low, high = max(low, 0.0), min(high, height - h)
        if low <= high + 1e-9:
            y0 = min(max(want_y, low), high)
            if abs(y0 - want_y) > 1:
                notes.append(f"aimed {'higher' if y0 < want_y else 'lower'} by {abs(y0 - want_y):.0f} px to keep "
                             + (top_name if y0 < want_y else bottom_name))
            if z < zoom - 1e-9:
                notes.append(f"zoom lowered from {zoom:.2f} to {z:.2f}: there isn't room for more while keeping "
                             + top_name + (" and " + bottom_name if caption_top is not None else ""))
            return round(z, 3), x0, y0, notes
        z = round(z - 0.01, 3)
    return None, 0, 0, [f"no room for even a {MIN_ZOOM:.2f} push without cutting the head: skip the push here"]


def filter_line(width, height, fps, start, end, zoom, x0, y0, duration, back):
    """A perspective filter that moves the visible area from the full frame to the crop and back, eased."""
    t = f"(in/{fps:.6f})"
    def smooth(x):
        return f"(3*pow({x},2)-2*pow({x},3))"
    ramp_in = smooth(f"clip(({t}-{start:.3f})/{duration:.3f},0,1)")
    ramp_out = smooth(f"clip(({end:.3f}-{t})/{back:.3f},0,1)") if back > 0 else f"lt({t},{end:.3f})"
    p = f"({ramp_in}*{ramp_out})"
    z = f"(1+{zoom - 1:.4f}*{p})"
    k = f"((1-1/{z})/{1 - 1 / zoom:.6f})"  # 0 at the full frame, 1 at full zoom
    left, top = f"({x0:.3f}*{k})", f"({y0:.3f}*{k})"
    right, bottom = f"({left}+{width}/{z})", f"({top}+{height}/{z})"
    corners = [(left, top), (right, top), (left, bottom), (right, bottom)]
    args = ":".join(f"x{i}='{x}':y{i}='{y}'" for i, (x, y) in enumerate(corners))
    return f"perspective={args}:interpolation=cubic:eval=frame:enable='between(t,{start:.3f},{end:.3f})'"


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "json", video], capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"Can't read {video}: {out.stderr.strip()}")
    s = json.loads(out.stdout)["streams"][0]
    return s["width"], s["height"], float(Fraction(s["r_frame_rate"]))


def find_face(video, at, model):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "retouch"))
    from facetrack import EdgeFace

    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "frame.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", video, "-frames:v", "1", png], check=True)
        frame = cv2.imread(png)
    if frame is None:
        sys.exit(f"Can't read a frame of {video} at {at:.2f} s.")
    height, width = frame.shape[:2]
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    with FaceLandmarker.create_from_options(FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model),
                                                                  num_faces=1)) as lm:
        found = lm.detect(image).face_landmarks
    if found:
        pts = [(p.x * width, p.y * height) for p in found[0]]
    else:
        edge = EdgeFace(model)
        points = edge.detect(frame)
        edge.close()
        if points is None:
            sys.exit("No face found where the push starts: start it a moment later, or skip it.")
        pts = [tuple(p) for p in points]
    face_h = pts[152][1] - pts[10][1]
    return {"centre_x": (pts[33][0] + pts[263][0]) / 2, "centre_y": (pts[10][1] + pts[152][1]) / 2,
            "head_top": pts[10][1] - 0.45 * face_h, "forehead": pts[10][1], "chin": pts[152][1], "mouth": pts[17][1]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("face_model")
    ap.add_argument("--at", type=float, help="when the push starts, in seconds")
    ap.add_argument("--until", type=float, help="when it ends (back to the full frame)")
    ap.add_argument("--say", help="a phrase from captions.json where the push starts")
    ap.add_argument("--until-say", help="with --say: the phrase where it ends")
    ap.add_argument("--captions", default="captions.json")
    ap.add_argument("--zoom", type=float, default=1.15)
    ap.add_argument("--duration", type=float, default=1.5, help="seconds to move in")
    ap.add_argument("--back", type=float, default=0.4, help="seconds to move back out at the end (0: cut back)")
    ap.add_argument("--caption-top", type=int, help="where the caption area starts (my-setup.md)")
    ap.add_argument("--out", default="pushin.txt")
    a = ap.parse_args()

    if a.say:
        start, end = times_from_captions(a.captions, a.say, a.until_say)
        if a.until is not None:
            end = a.until
    elif a.at is not None:
        start, end = a.at, a.until
    else:
        sys.exit("Give --at <seconds> or --say \"<phrase>\".")
    width, height, fps = probe(a.video)
    if end is None:
        sys.exit("Give --until <seconds> (or use --say, which ends with the caption).")
    if end - start < 0.5:
        sys.exit(f"The part from {start:.2f} to {end:.2f} s is too short for a push.")
    duration = min(a.duration, (end - start) * (0.6 if a.back > 0 else 1))
    back = min(a.back, end - start - duration)
    face = find_face(a.video, start, a.face_model)
    zoom, x0, y0, notes = aim(face, width, height, a.zoom, a.caption_top)
    for note in notes:
        print("Note:", note)
    if zoom is None:
        sys.exit(1)
    line = filter_line(width, height, fps, start, end, zoom, x0, y0, duration, back)
    open(a.out, "w", encoding="utf-8").write(line + "\n")
    print(f"Push in to {zoom:.2f} from {start:.2f} s (over {duration:.2f} s), "
          + (f"easing back out by {end:.2f} s." if back > 0 else f"cutting back at {end:.2f} s."))
    print(f"Wrote {a.out}. Put its line first in the picture chain of the text-and-graphics render.")


if __name__ == "__main__":
    main()
