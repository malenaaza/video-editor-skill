"""Find the face in the cover's background frame, for CoverCard's "around" layout.

Usage: python -I face_box.py <frame.png> <face_landmarker.task>

Prints the props to copy into cover.json, in pixels of that frame:
  {"faceX": ..., "faceY": ..., "faceSize": ...}
faceX/faceY is the middle of the face, faceSize the forehead-to-chin height.
Exits with an error if no face is found: pick another frame, or use the row layout.
"""
import json
import sys

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions

FRAME, MODEL = sys.argv[1], sys.argv[2]

bgr = cv2.imread(FRAME)
if bgr is None:
    sys.exit(f"Can't read {FRAME}")
h, w = bgr.shape[:2]
opts = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=MODEL), num_faces=1)
with FaceLandmarker.create_from_options(opts) as lm:
    result = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
if not result.face_landmarks:
    sys.exit("No face found in this frame: pick another frame, or use the row layout.")

p = result.face_landmarks[0]
xs = [pt.x * w for pt in p]
forehead, chin = p[10], p[152]
print(json.dumps({
    "faceX": round((min(xs) + max(xs)) / 2),
    "faceY": round((forehead.y + chin.y) / 2 * h),
    "faceSize": round(abs(chin.y - forehead.y) * h),
}))
