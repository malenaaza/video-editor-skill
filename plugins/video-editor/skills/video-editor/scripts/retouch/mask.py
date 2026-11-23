"""Writes per-frame skin and teeth masks as FFV1 grayscale videos (skin.mkv, teeth.mkv), plus
skin_strong.mkv: extra softening for close-ups, weighted by how big the face is in the frame.
spots.mkv: where freckles (spot_calm) and the glitter of shimmery makeup (shimmer_calm) get less contrast (spots.py).

Usage (from the folder with the clean render): python -I mask.py <face_landmarker.task> [clean.mp4]

Don't edit this file for a video. Its levels come from retouch.json in the folder you run it
from (see settings.py for every setting and its default); with no retouch.json, the defaults.

Skin is found inside the tracked face oval by colour (YCrCb red channel), with the eyes,
brows, lips and mouth protected. skin_cr_min and lips_cr_min were tuned on one person's
light-to-medium skin. They will need adjusting for other skin tones: look at a test frame
of skin.mkv, and lower skin_cr_min if parts of the face are missing from the mask, or raise it
if hair or background is included.

The skin area covers the face oval and, with neck true, the neck under the jaw.
skin_cr_max keeps very red pixels out (a red top or scarf), which aren't skin.
Close-ups: when the face is big in the frame, skin texture is magnified and the normal level
isn't enough. skin_strong.mkv ramps from 0 (face height below close_lo of the frame height) to
full (above close_hi), smoothed from frame to frame so it doesn't flicker. retouch.txt adds a
second, stronger softening on top of the normal one where this mask allows, then
a last pass that calms the spots (input 4, spots.mkv).
"""
import os
import subprocess
import sys
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker,
    FaceLandmarkerOptions,
    RunningMode,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
from facetrack import EdgeFace  # noqa: E402
import beauty  # noqa: E402
import spots  # noqa: E402
import feather  # noqa: E402

CFG = settings.load()
MODEL = sys.argv[1]
SOURCE = sys.argv[2] if len(sys.argv) > 2 else "clean.mp4"
SKIN_STRENGTH = CFG["skin_strength"]
SKIN_CR_MIN = CFG["skin_cr_min"]
SKIN_CR_MAX = CFG["skin_cr_max"]
LIPS_CR_MIN = CFG["lips_cr_min"]

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
NECK = CFG["neck"]
CLOSE_LO, CLOSE_HI = CFG["close_lo"], CFG["close_hi"]  # face height (forehead 10 to chin 152) as a share of frame height
JAW = [234, 93, 132, 58, 172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323, 454]
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
strong_out = writer("skin_strong.mkv", width, height, fps)
spots_out = writer("spots.mkv", width, height, fps)
under_out = writer("undereye.mkv", width, height, fps) if CFG["under_eye"] > 0 else None
white_out = writer("eyewhite.mkv", width, height, fps) if CFG["eye_white"] > 0 else None
weight = 0.0  # smoothed close-up weight

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL),
    running_mode=RunningMode.VIDEO,
    num_faces=1,
)
previous = None
frame_number = 0
started = time.perf_counter()
missed = 0
edge = EdgeFace(MODEL, CFG["edge_faces"], CFG["edge_pad"])
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
        strong = np.zeros(shape, np.uint8)
        spot = np.zeros(shape, np.uint8)
        under = np.zeros(shape, np.uint8)
        white = np.zeros(shape, np.uint8)
        points = None
        if result.face_landmarks:
            points = np.array(
                [[p.x * width, p.y * height] for p in result.face_landmarks[0]],
                np.float32,
            )
        else:
            points = edge.detect(frame)  # a face cut in half by the frame edge
        if points is not None:
            if previous is not None and np.abs(points - previous).mean() < 12:
                points = previous * 0.4 + points * 0.6
            previous = points
            pts = points.astype(np.int32)

            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb).astype(np.float32)
            luma, red, blue = ycrcb[..., 0], ycrcb[..., 1], ycrcb[..., 2]

            # Warm, red-leaning pixels are skin; most backgrounds and objects are not.
            tone = np.clip((red - SKIN_CR_MIN) / 8, 0, 1)
            tone *= np.clip((SKIN_CR_MAX - red) / 8, 0, 1)
            region = poly(shape, pts[OVAL])
            gx, gy = CFG["region_grow"]
            if gx > 1 or gy > 1:
                # The outline of a turned face's far cheek lies inside the real cheek. Add the
                # skin-coloured pixels that touch the face, within a wider area around it.
                centre = pts[OVAL].mean(axis=0)
                wide = poly(shape, ((pts[OVAL] - centre) * np.array([gx, gy], np.float32) + centre).astype(np.int32))
                skin_like = ((tone > 0.5) & (wide > 0)).astype(np.uint8) * 255
                skin_like = cv2.morphologyEx(skin_like, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
                joined = cv2.bitwise_or(skin_like, region)
                _, labels = cv2.connectedComponents(joined)
                nose = labels[min(max(int(pts[1][1]), 0), shape[0] - 1), min(max(int(pts[1][0]), 0), shape[1] - 1)]
                if nose > 0:
                    region = ((labels == nose) * 255).astype(np.uint8)
            face_h = float(points[152][1] - points[10][1])
            if NECK:
                # From the jaw line down about 0.75 face heights, a little wider than the jaw.
                jaw = pts[JAW].astype(np.float32)
                low = jaw.copy()
                low[:, 0] = jaw[:, 0].mean() + (low[:, 0] - jaw[:, 0].mean()) * 1.05
                low[:, 1] += face_h * 0.75
                cv2.fillPoly(region, [cv2.convexHull(np.vstack([jaw, low]).astype(np.int32))], 255)
            def hulls(groups):
                canvas = np.zeros(shape, np.uint8)
                for group in groups:
                    cv2.fillConvexPoly(canvas, cv2.convexHull(pts[group]), 255)
                return canvas

            def grow(canvas, size):
                if size <= 1:
                    return canvas
                return cv2.dilate(canvas, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))

            protect = cv2.dilate(hulls((LIPS, MOUTH)), kernel)
            protect = cv2.bitwise_or(protect, grow(hulls((EYE_L, EYE_R)), int(CFG["protect_eyes"])))
            brow_area = hulls((BROW_L, BROW_R))
            hair_keep = None
            if CFG["brow_mode"] == "hair":
                # Protect only the dark brow hairs (strokes attached to the brow). The skin between and around them
                # is smoothed, and so is a freckle beside the brow: it is not a hair (spots.py).
                hair_keep = spots.brow_hair_keep(luma, brow_area, CFG["brow_contrast"], face_h)
            else:
                protect = cv2.bitwise_or(protect, grow(brow_area, int(CFG["protect_brows"])))
            # The outer edge fades over a share of the face's height (feather.py), so on a close-up the smoothing
            # doesn't stop at a line across the forehead; the eyes, lips and mouth keep their own 9 px edges.
            mask = feather.soft_skin((region.astype(np.float32) / 255) * tone, tone,
                                     1 - protect.astype(np.float32) / 255, face_h, CFG["forehead_feather"])
            if hair_keep is not None:
                mask *= 1 - hair_keep
            skin = np.clip(mask * SKIN_STRENGTH * 255, 0, 255).astype(np.uint8)
            if CFG["spot_calm"] > 0 or CFG["shimmer_calm"] > 0:
                # Small dark spots (freckles, off by default) and small bright specks (the glitter of a shimmery
                # eyeshadow or highlighter) keep only part of their contrast: retouch.txt blends a median-smoothed
                # copy through this mask. Not the eyes, lips, mouth, brow or its hairs, nor moles or real reflections.
                left_alone = (protect > 0) | (brow_area > 0)
                if hair_keep is not None:
                    left_alone |= hair_keep > 0.2
                calm = np.zeros(shape, np.float32)
                if CFG["spot_calm"] > 0:
                    calm = spots.spot_mask(luma, mask, left_alone, face_h, CFG["spot_contrast"]) * CFG["spot_calm"]
                if CFG["shimmer_calm"] > 0:
                    calm = np.maximum(calm, spots.spot_mask(luma, mask, left_alone, face_h, CFG["shimmer_contrast"],
                                                            bright=True) * CFG["shimmer_calm"])
                spot = np.clip(calm * 255, 0, 255).astype(np.uint8)
            target = min(max((face_h / height - CLOSE_LO) / (CLOSE_HI - CLOSE_LO), 0.0), 1.0)
            weight = weight * 0.85 + target * 0.15
            strong = np.clip(mask * weight * 255, 0, 255).astype(np.uint8)
            if under_out is not None:
                under = beauty.under_eye(pts.astype(np.float32), shape)
            if white_out is not None:
                white = beauty.eye_whites(frame, luma, pts.astype(np.float32), shape)

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
        strong_out.stdin.write(strong.tobytes())
        spots_out.stdin.write(spot.tobytes())
        if under_out is not None:
            under_out.stdin.write(under.tobytes())
        if white_out is not None:
            white_out.stdin.write(white.tobytes())
        frame_number += 1

capture.release()
skin_out.stdin.close()
teeth_out.stdin.close()
strong_out.stdin.close()
spots_out.stdin.close()
for extra in (under_out, white_out):
    if extra is not None:
        extra.stdin.close()
skin_out.wait()
teeth_out.wait()
strong_out.wait()
spots_out.wait()
for extra in (under_out, white_out):
    if extra is not None:
        extra.wait()
edge.close()
print(f"frames {frame_number}, no face {missed}, found at the frame edge {edge.found}, teeth visible {open_frames}")
spent = time.perf_counter() - started
# so a slow machine, or an extra that costs a lot, shows up (references/retouch.md, What the masks cost)
print(f"masks: {spent / max(frame_number, 1) * 1000:.0f} ms a frame, {spent / 60:.1f} min in all")
