"""Mouth check (Rule 3): flag stretches where the speaker's mouth is closed or still.

Usage: mouth.py <video> <face_landmarker.task> [min_seconds=0.4]
Writes mouth.json (per-frame opening, None where no face) and prints flagged
stretches in video seconds. Opening = inner-lip gap (landmarks 13-14) divided
by face height (10-152), so zooms don't change it.
"""
import json
import sys

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

VIDEO, MODEL = sys.argv[1], sys.argv[2]
MIN_S = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4

cap = cv2.VideoCapture(VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS) or 24
opts = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL),
                             running_mode=RunningMode.VIDEO, num_faces=1)
values = []
with FaceLandmarker.create_from_options(opts) as lm:
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        r = lm.detect_for_video(img, int(n * 1000 / fps))
        if r.face_landmarks:
            p = r.face_landmarks[0]
            gap = np.hypot(p[13].x - p[14].x, (p[13].y - p[14].y) * frame.shape[0] / frame.shape[1])
            face = np.hypot(p[10].x - p[152].x, (p[10].y - p[152].y) * frame.shape[0] / frame.shape[1])
            values.append(float(gap / face) if face > 0 else None)
        else:
            values.append(None)
        n += 1
json.dump(values, open("mouth.json", "w"))

v = np.array([x if x is not None else np.nan for x in values])
found = ~np.isnan(v)
print(f"frames {len(v)}, no face {int((~found).sum())}")
closed_thr = np.nanpercentile(v, 15)
print(f"opening percentiles 10/25/50/90: " + " ".join(f"{np.nanpercentile(v, q):.3f}" for q in (10, 25, 50, 90)))
# still = closed (below the 15th percentile) or barely changing over a 0.25 s window
win = max(3, int(fps * 0.25))
motion = np.array([np.nanmax(v[max(0, i - win):i + win]) - np.nanmin(v[max(0, i - win):i + win])
                   if found[i] else np.nan for i in range(len(v))])
still = found & ((v < closed_thr) | (motion < 0.012))
minf = int(MIN_S * fps)
i = 0
print(f"stretches >= {MIN_S}s with mouth closed or still:")
while i < len(v):
    if still[i]:
        j = i
        while j < len(v) and still[j]:
            j += 1
        if j - i >= minf:
            print(f"  {i / fps:7.2f}-{j / fps:7.2f} ({(j - i) / fps:.2f}s) mean opening {np.nanmean(v[i:j]):.3f}")
        i = j
    else:
        i += 1
i = 0
print("stretches >= 0.4 s with no face (check against transcripts):")
while i < len(v):
    if not found[i]:
        j = i
        while j < len(v) and not found[j]:
            j += 1
        if j - i >= minf:
            print(f"  {i / fps:7.2f}-{j / fps:7.2f}")
        i = j
    else:
        i += 1
