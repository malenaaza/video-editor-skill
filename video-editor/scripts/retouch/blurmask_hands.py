"""Soft background mask (white = blur) with face and hand tracking, for close-framed hauls.

Keeps sharp: head and hair, neck, skin, the clothing colour given as a key in retouch.json
("blur_keys", see settings.py), and a generous area around each tracked hand so held products
stay sharp whatever their colour. Don't edit this file for a video: put the clothing key in
retouch.json in the folder you run this from.

Usage: python -I blurmask_hands.py <source.mp4> <out.mkv> <face model> <hand model> write|test [test frames]
"write" builds the mask (and a test sheet if frames are given); "test" stops after the last test frame.
Works at half resolution for speed (about 0.17 s per frame on a laptop CPU).
"""
import os
import subprocess
import sys

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker, FaceLandmarkerOptions, HandLandmarker, HandLandmarkerOptions, RunningMode,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402
from facetrack import EdgeFace  # noqa: E402

CFG = settings.load()
SOURCE, OUT, FACE_MODEL, HAND_MODEL = sys.argv[1:5]
TEST = [int(x) for x in sys.argv[6:]]
WRITE = sys.argv[5] == "write"  # "write" builds the mask; "test" stops after the last test frame
OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379,
        378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
        162, 21, 54, 103, 67, 109]
HAND_PAD = CFG["hand_pad"]    # pixels kept around a hand, for the product it holds
HAND_HOLD = CFG["hand_hold"]  # frames to keep a hand after tracking loses it


def ellipse(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def color_keys(frame, height):
    skin = CFG["blur_skin"] or {"a": [13, None], "b": [13, None], "lum": [91, None], "sat": [51, None]}
    mask = settings.key_mask(frame, [skin] + CFG["blur_keys"]).astype(np.uint8) * 255
    below = 0.45 if CFG["blur_keys_below"] is None else CFG["blur_keys_below"]
    mask[: int(height * below)] = 0
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, ellipse(7))


def keep_mask(frame, face, hands, shape):
    keep = color_keys(frame, shape[0])
    if face is not None:
        center = face[OVAL].mean(axis=0)
        head = (face[OVAL] - center) * np.array([1.32, 1.42], np.float32) + center
        head[:, 1] -= 12
        cv2.fillConvexPoly(keep, cv2.convexHull(head.astype(np.int32)), 255)
        if CFG["crown"]:  # a tall headband or hair above the head
            oval_h = face[OVAL][:, 1].max() - face[OVAL][:, 1].min()
            crown = (face[OVAL] - center) * np.array(CFG["crown"]["grow"], np.float32) + center
            crown[:, 1] -= CFG["crown"]["raise"] * oval_h
            cv2.fillConvexPoly(keep, cv2.convexHull(crown.astype(np.int32)), 255)
        chin = face[OVAL][:, 1].max()
        left, right = face[OVAL][:, 0].min(), face[OVAL][:, 0].max()
        neck = np.array([[left + 15, chin - 40], [right - 15, chin - 40],
                         [right + 30, chin + 130], [left - 30, chin + 130]], np.int32)
        cv2.fillConvexPoly(keep, neck, 255)
    hand_layer = np.zeros(shape, np.uint8)
    for points in hands:
        cv2.fillConvexPoly(hand_layer, cv2.convexHull(points.astype(np.int32)), 255)
    if hands:
        hand_layer = cv2.dilate(hand_layer, ellipse(HAND_PAD * 2 + 1))
        keep = cv2.bitwise_or(keep, hand_layer)
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, ellipse(21))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(keep, connectivity=8)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] < 2250:
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
if WRITE:
    writer = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
         "-s", f"{width}x{height}", "-r", f"{fps}", "-i", "-", "-c:v", "ffv1", OUT],
        stdin=subprocess.PIPE,
    )
face_options = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=FACE_MODEL),
                                     running_mode=RunningMode.VIDEO, num_faces=1)
hand_options = HandLandmarkerOptions(base_options=BaseOptions(model_asset_path=HAND_MODEL),
                                     running_mode=RunningMode.VIDEO, num_hands=2,
                                     min_hand_detection_confidence=0.4,
                                     min_tracking_confidence=0.4)
edge = EdgeFace(FACE_MODEL, CFG["edge_faces"], CFG["edge_pad"])
face_points, last_hands, hand_age = None, [], 0
previous, tiles = None, []
hand_frames = no_face = 0
with FaceLandmarker.create_from_options(face_options) as face_tracker, \
        HandLandmarker.create_from_options(hand_options) as hand_tracker:
    n = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if not WRITE and TEST and n > max(TEST):
            break
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        stamp = int(n * 1000 / fps)
        result = face_tracker.detect_for_video(image, stamp)
        if result.face_landmarks:
            face_points = np.array([[p.x * width, p.y * height] for p in result.face_landmarks[0]], np.float32)
        else:
            cut_off = edge.detect(frame)  # a face cut in half by the frame edge
            if cut_off is not None:
                face_points = cut_off
            else:
                no_face += 1
        found = hand_tracker.detect_for_video(image, stamp).hand_landmarks
        if found:
            last_hands = [np.array([[p.x * width, p.y * height] for p in h], np.float32) for h in found]
            hand_age = 0
            hand_frames += 1
        else:
            hand_age += 1
            if hand_age > HAND_HOLD:
                last_hands = []
        small = cv2.resize(frame, (width // 2, height // 2), interpolation=cv2.INTER_AREA)
        keep = keep_mask(small, None if face_points is None else face_points / 2,
                         [h / 2 for h in last_hands], (height // 2, width // 2))
        keep = cv2.resize(keep, (width, height), interpolation=cv2.INTER_LINEAR)
        soft = cv2.GaussianBlur(keep.astype(np.float32) / 255, (0, 0), 7)
        if previous is not None and np.abs(soft - previous).mean() < 0.04:
            soft = previous * 0.5 + soft * 0.5
        previous = soft
        blur_amount = 1 - np.clip(soft * 1.15, 0, 1)
        if writer:
            writer.stdin.write((blur_amount * 255).astype(np.uint8).tobytes())
        if n in TEST:
            blurred = cv2.GaussianBlur(frame, (0, 0), 9)
            a = blur_amount[..., None]
            shown = (frame * (1 - a) + blurred * a).astype(np.uint8)
            tint = shown.copy()
            tint[..., 2] = np.clip(tint[..., 2] + (a[..., 0] * 90), 0, 255)
            tiles.append(cv2.resize(np.hstack([shown, tint]), (540, 480)))
        n += 1
if writer:
    writer.stdin.close()
    writer.wait()
if tiles:
    rows = [np.hstack(tiles[i:i + 3] + [np.zeros_like(tiles[0])] * (3 - len(tiles[i:i + 3])))
            for i in range(0, len(tiles), 3)]
    cv2.imwrite("blurtest.png", np.vstack(rows))
edge.close()
print(f"frames {n}, hands seen {hand_frames}, no face {no_face}, faces found at the frame edge {edge.found}")
