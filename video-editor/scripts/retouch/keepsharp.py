"""Remove the blur from a fixed area of an existing background mask, such as a brand prop
that should stay sharp. Optionally follows each shot's punch-in zoom.

Usage: python -I keepsharp.py <bgmask.mkv> <out.mkv> "<polygon>" [plan.json]

  polygon    the prop's outline in output pixels, as JSON: "[[0,236],[332,240],[360,545],[0,676]]"
             Read the points off a frame with a grid drawn on it.
  plan.json  optional: {"frames": [[first_frame, end_frame, zoom], ...]} for the kept pieces,
             in output order. Each zoom ramps in over ZOOM_RAMP_S, centred horizontally and
             anchored ZOOM_ANCHOR_Y down the frame. Change both to match how your zooms are made.

Check a zoomed shot afterwards, because the prop shifts there.
"""
import json
import subprocess
import sys

import cv2
import numpy as np

ZOOM_RAMP_S = 0.2
ZOOM_ANCHOR_Y = 0.35

src, dst, polygon = sys.argv[1], sys.argv[2], np.array(json.loads(sys.argv[3]), np.float32)
probe = json.loads(subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
     "-of", "json", src], capture_output=True, text=True).stdout)["streams"][0]
W, H = probe["width"], probe["height"]
num, den = map(int, probe["r_frame_rate"].split("/"))
FPS = num / den

zooms = None
if len(sys.argv) > 4:
    zooms = []
    for a, b, z in json.load(open(sys.argv[4], encoding="utf-8"))["frames"]:
        for k in range(b - a):
            zooms.append(1 + (z - 1) * min(k / FPS / ZOOM_RAMP_S, 1))

reader = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                          stdout=subprocess.PIPE)
writer = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                           "-r", f"{FPS}", "-i", "-", "-c:v", "ffv1", dst], stdin=subprocess.PIPE)
cache = {}
n = 0
while True:
    buf = reader.stdout.read(W * H)
    if len(buf) < W * H:
        break
    z = round(zooms[n], 4) if zooms and n < len(zooms) else 1.0
    if z not in cache:
        pts = polygon.copy()
        pts[:, 0] = (pts[:, 0] - W / 2) * z + W / 2
        pts[:, 1] = pts[:, 1] * z - (H * z - H) * ZOOM_ANCHOR_Y
        keep = np.zeros((H, W), np.uint8)
        cv2.fillPoly(keep, [pts.astype(np.int32)], 255)
        cache[z] = 1 - cv2.GaussianBlur(keep.astype(np.float32) / 255, (0, 0), 6)
    m = np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.float32) * cache[z]
    writer.stdin.write(m.astype(np.uint8).tobytes())
    n += 1
writer.stdin.close()
writer.wait()
print("frames", n, "expected", len(zooms) if zooms else n)
