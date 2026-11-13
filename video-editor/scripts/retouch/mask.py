"""Writes per-frame skin and teeth masks as FFV1 grayscale videos (skin.mkv, teeth.mkv).

Usage (from the folder with the clean render): python -I mask.py <face_landmarker.task> [clean.mp4]

Skin is found inside the tracked face oval by colour (YCrCb red channel), with the eyes,
brows, lips and mouth protected. SKIN_CR_MIN and LIPS_CR_MIN were tuned on one person's
light-to-medium skin. They will need adjusting for other skin tones: look at a test frame
of skin.mkv, and lower SKIN_CR_MIN if parts of the face are missing from the mask, or raise it
if hair or background is included.
"""
import subprocess
import sys

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,
)

MODEL = sys.argv[1]
SOURCE = sys.argv[2] if len(sys.argv) > 2 else "clean.mp4"
SKIN_STRENGTH = 0.88  # 0 = no softening, 1 = full
SKIN_CR_MIN = 139    # YCrCb red level where skin starts (see above)
LIPS_CR_MIN = 146    # lips redder than this count as visible (teeth only whiten then)

OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379,
        378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
        162, 21, 54, 103, 67, 109]
EYE_L = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
EYE_R = [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249]
BROW_L = [46, 53, 52, 65, 55, 70, 63, 105, 66, 107]
BROW_R = [276, 283, 282, 295, 285, 300, 293, 334, 296, 336]
LIPS = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0,
        37, 39, 40, 185]
MOUTH = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13,
         82, 81, 80, 191]
NOSE = [64, 98, 97, 2, 326, 327, 294, 278, 344, 440, 275, 4, 45, 220, 115, 48]


def writer(path, width, height, fps):
    return subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
         "-s", f"{width}x{height}", "-r", f"{fps}", "-i", "-", "-c:v", "ffv1", path],
        stdin=subprocess.PIPE,
    )


def poly(shape, points):
    canvas = np.zeros(shape, np.uint8)
    cv2.fillPoly(canvas, [points], 255)
    return canvas


capture = cv2.VideoCapture(SOURCE)
width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = capture.get(cv2.CAP_PROP_FPS) or 24
skin_out = writer("skin.mkv", width, height, fps)
teeth_out = writer("teeth.mkv", width, height, fps)

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL),
    running_mode=RunningMode.VIDEO,
    num_faces=1,
)
previous = None
frame_number = 0
missed = 0
open_frames = 0
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))

with FaceLandmarker.create_from_options(options) as tracker:
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = tracker.detect_for_video(image, int(frame_number * 1000 / fps))
        shape = frame.shape[:2]
        skin = np.zeros(shape, np.uint8)
        teeth = np.zeros(shape, np.uint8)
        if result.face_landmarks:
            points = np.array(
                [[p.x * width, p.y * height] for p in result.face_landmarks[0]],
                np.float32,
            )
            if previous is not None and np.abs(points - previous).mean() < 12:
                points = previous * 0.4 + points * 0.6
            previous = points
            pts = points.astype(np.int32)

            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb).astype(np.float32)
            luma, red, blue = ycrcb[..., 0], ycrcb[..., 1], ycrcb[..., 2]

            # Warm, red-leaning pixels are skin; most backgrounds and objects are not.
            tone = np.clip((red - SKIN_CR_MIN) / 8, 0, 1)
            region = poly(shape, pts[OVAL])
            protect = np.zeros(shape, np.uint8)
            for group in (EYE_L, EYE_R, BROW_L, BROW_R, LIPS, MOUTH):
                hull = cv2.convexHull(pts[group])
                cv2.fillConvexPoly(protect, hull, 255)
            protect = cv2.dilate(protect, kernel)
            mask = (region.astype(np.float32) / 255) * tone
            mask *= 1 - protect.astype(np.float32) / 255
            mask = cv2.GaussianBlur(mask, (0, 0), 9)
            skin = np.clip(mask * SKIN_STRENGTH * 255, 0, 255).astype(np.uint8)

            mouth = poly(shape, pts[MOUTH])
            # Lips are red. If they aren't, something is in front of the mouth.
            lip_band = (poly(shape, pts[LIPS]) > 0) & (mouth == 0)
            lips_visible = lip_band.any() and red[lip_band].mean() > LIPS_CR_MIN
            if cv2.countNonZero(mouth) > 500 and lips_visible:
                inner = cv2.erode(
                    mouth, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                ).astype(np.float32) / 255
                bright = np.clip((luma - 88) / 26, 0, 1)
                pale = np.clip((156 - red) / 8, 0, 1)
                gate = cv2.GaussianBlur(inner * bright * pale, (0, 0), 1.6)
                teeth = np.clip(gate * 255, 0, 255).astype(np.uint8)
                if teeth.max() > 80:
                    open_frames += 1
        else:
            missed += 1
            previous = None
        skin_out.stdin.write(skin.tobytes())
        teeth_out.stdin.write(teeth.tobytes())
        frame_number += 1

capture.release()
skin_out.stdin.close()
teeth_out.stdin.close()
skin_out.wait()
teeth_out.wait()
print(f"frames {frame_number}, no face {missed}, teeth visible {open_frames}")
