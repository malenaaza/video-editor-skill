"""Writes a soft background mask (bgmask.mkv): white is blurred, black stays sharp.

Usage (from the folder with the source): python -I blurmask.py <face_landmarker.task> [frame numbers to test]
With frame numbers it only writes a test sheet, bg/blurtest.png. Without, it builds bgmask.mkv.

Keeps sharp: the tracked head and neck, plus anything matching color_keys(). Edit
color_keys() for each video: sample the held object and the clothing in Lab and HSV
on a frame first, because guessed values fail. The example key below is for a
cardboard box (Lab a 1..9, b 4..20, hue 9..24).
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
TEST = [int(x) for x in sys.argv[2:]]
SOURCE = "retouched.mp4"  # the clean render to build the mask from
OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379,
        378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
        162, 21, 54, 103, 67, 109]


def ellipse(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def color_keys(frame, height):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.int16)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.int16)
    lum, a, b = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    skin = (a > 15) & (b > 10) & (lum > 95)  # tune for the speaker's skin tone
    # Example extra key, a held cardboard box. Replace or add keys for each video:
    held = (lum > 105) & (a > 1) & (a < 9) & (b > 4) & (b < 20) & (hue >= 9) & (hue <= 24) & (sat < 95)
    mask = (skin | held).astype(np.uint8) * 255
    mask[: int(height * 0.42)] = 0  # colour keys only count in the lower part of the frame
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, ellipse(15))


def keep_mask(frame, points, shape):
    keep = color_keys(frame, shape[0])
    if points is not None:
        center = points[OVAL].mean(axis=0)
        scale = np.array([1.28, 1.34], np.float32)
        head = ((points[OVAL] - center) * scale + center).astype(np.int32)
        cv2.fillConvexPoly(keep, cv2.convexHull(head), 255)
        chin = points[OVAL][:, 1].max()
        left, right = points[OVAL][:, 0].min(), points[OVAL][:, 0].max()
        neck = np.array(
            [[left + 30, chin - 80], [right - 30, chin - 80],
             [right + 20, chin + 180], [left - 20, chin + 180]],
            np.int32,
        )
        cv2.fillConvexPoly(keep, neck, 255)
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, ellipse(41))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(keep, connectivity=8)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] < 9000:
            keep[labels == label] = 0
    outlines = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    filled = np.zeros(shape, np.uint8)
    cv2.drawContours(filled, outlines, -1, 255, thickness=cv2.FILLED)
    return filled


capture = cv2.VideoCapture(SOURCE)
width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
shape = (height, width)
fps = capture.get(cv2.CAP_PROP_FPS) or 24
writer = None
if not TEST:
    writer = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
         "-s", f"{width}x{height}", "-r", f"{fps}", "-i", "-", "-c:v", "ffv1", "bgmask.mkv"],
        stdin=subprocess.PIPE,
    )

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL),
    running_mode=RunningMode.VIDEO,
    num_faces=1,
)
last_points = None
previous = None
tiles = []
with FaceLandmarker.create_from_options(options) as tracker:
    n = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = tracker.detect_for_video(image, int(n * 1000 / fps))
        if result.face_landmarks:
            last_points = np.array(
                [[p.x * width, p.y * height] for p in result.face_landmarks[0]],
                np.float32,
            )
        keep = keep_mask(frame, last_points, shape)
        soft = cv2.GaussianBlur(keep.astype(np.float32) / 255, (0, 0), 7)
        if previous is not None and np.abs(soft - previous).mean() < 0.04:
            soft = previous * 0.5 + soft * 0.5
        previous = soft
        blur_amount = 1 - np.clip(soft * 1.15, 0, 1)
        if writer:
            writer.stdin.write((blur_amount * 255).astype(np.uint8).tobytes())
        elif n in TEST:
            blurred = cv2.GaussianBlur(frame, (0, 0), 9)
            a = blur_amount[..., None]
            out = (frame * (1 - a) + blurred * a).astype(np.uint8)
            tiles.append(cv2.resize(out, (300, 533)))
        n += 1

if writer:
    writer.stdin.close()
    writer.wait()
else:
    import os
    os.makedirs("bg", exist_ok=True)
    cv2.imwrite("bg/blurtest.png", np.hstack(tiles))
print("frames", n)
