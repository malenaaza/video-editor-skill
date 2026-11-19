"""Checks whether the background is already blurred (a phone's Cinematic or Portrait mode, or a camera lens wide
open), so the skill doesn't offer to blur it again.

  <face python> -I blurcheck.py <video> <face_landmarker.task> [--frames 8] [--out blurcheck.json]

On a few frames spread through the video it finds the face and compares how crisp the strongest edges are beside and
above the head (the background) with those in the face (eyes, brows, lips): the 95th percentile of the Laplacian,
the usual focus measure. It prints the background-to-face ratio and a verdict:
  already soft   (under 0.35) the background is blurred already, or plain with nothing to blur: don't offer blur
  a little soft  (0.35 to 0.6) say it's slightly soft already; blur only if the user wants it softer
  sharp          (over 0.6)    background blur can help, as the brand's Look line says
Measured on a real clip: the sharp original 1.05, the same clip with the skill's background blur 0.19.

A phone's Cinematic or Portrait mode decides what to blur by guessing the speaker's outline, and it can blur a product
held towards the camera; that blur is in the recording and can't be undone. When the background is already soft,
look at a frame where a product is held up: if it's soft too, tell the user (references/retouch.md). Needs OpenCV,
MediaPipe and FFmpeg for the frames and the face; the measure itself is numpy.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

SOFT, LITTLE = 0.35, 0.6


def edge_strength(gray):
    """95th percentile of the absolute Laplacian of a grey image (float array): how crisp its strongest edges are."""
    g = gray.astype(np.float32)
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    return float(np.percentile(lap, 95)) if lap.size else 0.0


def regions(width, height, face):
    """The face's inner box and the background boxes beside and above the head. face: (x0, y0, x1, y1) in pixels,
    forehead to chin. Boxes are (x0, y0, x1, y1); background boxes too small to measure are left out."""
    x0, y0, x1, y1 = face
    fw, fh = x1 - x0, y1 - y0
    inner = (int(x0 + fw * 0.15), int(y0 + fh * 0.1), int(x1 - fw * 0.15), int(y1 - fh * 0.1))
    head_top = max(0, int(y0 - fh * 0.6))                # hair above the forehead isn't background
    side_y0, side_y1 = head_top, int(min(height, y1))
    gap = fw * 0.45                                      # leave out the hair and ears beside the face
    boxes = [(0, side_y0, int(max(0, x0 - gap)), side_y1),
             (int(min(width, x1 + gap)), side_y0, width, side_y1),
             (0, 0, width, max(0, int(head_top - fh * 0.15)))]
    min_area = 0.02 * width * height
    return inner, [b for b in boxes if (b[2] - b[0]) * (b[3] - b[1]) >= min_area]


def ratio(gray, face):
    """Background-to-face edge strength for one grey frame, or None when there's no background to measure."""
    h, w = gray.shape
    inner, bg = regions(w, h, face)
    face_edges = edge_strength(gray[inner[1]:inner[3], inner[0]:inner[2]])
    if not bg or face_edges <= 0:
        return None
    back = max(edge_strength(gray[b[1]:b[3], b[0]:b[2]]) for b in bg)   # the crispest background area decides
    return back / face_edges


def verdict(r):
    if r < SOFT:
        return "already soft"
    if r < LITTLE:
        return "a little soft"
    return "sharp"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("face_model")
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--out", default="blurcheck.json")
    a = ap.parse_args()

    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions

    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json",
                                      a.video], capture_output=True, text=True).stdout or "{}")
    duration = float(info.get("format", {}).get("duration", 0) or 0)
    if duration <= 0:
        sys.exit(f"Can't read {a.video}.")
    found = []
    opts = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=a.face_model), num_faces=1)
    with FaceLandmarker.create_from_options(opts) as lm:
        for k in range(a.frames):
            t = duration * (k + 0.5) / a.frames
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", a.video, "-frames:v", "1",
                                  "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
            frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) if raw else None
            if frame is None:
                continue
            h, w = frame.shape[:2]
            res = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            if not res.face_landmarks:
                continue
            pts = res.face_landmarks[0]
            xs = [p.x * w for p in pts]
            face = (min(xs), pts[10].y * h, max(xs), pts[152].y * h)
            r = ratio(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), face)
            if r is not None:
                found.append((round(t, 2), round(r, 3)))
    if not found:
        sys.exit("No frame with both a face and some background to measure (a very tight close-up?): "
                 "judge by eye from a frame.")
    median = float(np.median([r for _, r in found]))
    result = {"ratio": round(median, 3), "verdict": verdict(median), "frames": found}
    json.dump(result, open(a.out, "w", encoding="utf-8"), indent=1)
    print(f"Background-to-face sharpness: {median:.2f} over {len(found)} frames: {result['verdict']}.")
    if result["verdict"] == "already soft":
        print("The background is already blurred (or plain): don't offer background blur for this footage. If it "
              "was filmed in Cinematic or Portrait mode, check a frame where a product is held up: that mode can "
              "blur it, and the recording can't be fixed.")
    elif result["verdict"] == "a little soft":
        print("The background is already a little soft: offer blur only if the user wants it softer, at a lower level.")
    else:
        print("The background is sharp: background blur works as the brand's Look line says.")
    print(f"Wrote {os.path.basename(a.out)}.")


if __name__ == "__main__":
    main()
