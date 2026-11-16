"""Masks for the beautify extras: under-eye brightening and whiter eye whites.

Called by mask.py when those are on. No makeup and no reshaping: these only lift light a little, in
places the face tracker finds. Each mask is 0 to 255 and says where an effect applies; how strong it is
comes from the filter (beautify.py), so the same mask serves every level.
"""
import cv2
import numpy as np

# MediaPipe face mesh: lower lid curve and corners of each eye, upper-lid centre, iris centre and rim.
EYES = [
    {"lower": [33, 7, 163, 144, 145, 153, 154, 155, 133], "corners": (33, 133), "upper": 159, "lower_mid": 145,
     "iris": [468, 469, 470, 471, 472]},
    {"lower": [263, 249, 390, 373, 374, 380, 381, 382, 362], "corners": (263, 362), "upper": 386, "lower_mid": 374,
     "iris": [473, 474, 475, 476, 477]},
]
EYE_OUTLINE = [[33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7],
               [263, 466, 388, 387, 386, 385, 384, 398, 362, 382, 381, 380, 374, 373, 390, 249]]


def _eye_polygon(pts, group, shape):
    canvas = np.zeros(shape, np.uint8)
    cv2.fillConvexPoly(canvas, cv2.convexHull(pts[group].astype(np.int32)), 255)
    return canvas


def under_eye(pts, shape):
    """A soft band just below each lower lid (where dark circles sit), never inside the eye."""
    out = np.zeros(shape, np.float32)
    for eye, outline in zip(EYES, EYE_OUTLINE):
        lid = pts[eye["lower"]].astype(np.float32)
        a, b = eye["corners"]
        width = float(np.hypot(*(pts[a] - pts[b])))
        if width < 6:
            continue
        down = lid + np.array([0.0, 0.36 * width], np.float32)
        band = np.zeros(shape, np.uint8)
        cv2.fillPoly(band, [np.vstack([lid, down[::-1]]).astype(np.int32)], 255)
        band = band.astype(np.float32) / 255
        inside = _eye_polygon(pts, outline, shape).astype(np.float32) / 255
        soft = cv2.GaussianBlur(band * (1 - inside), (0, 0), max(1.0, 0.1 * width))
        soft *= 1 - cv2.GaussianBlur(inside, (0, 0), 1.5)  # the soft edge must not leak into the eye
        out = np.maximum(out, soft)
    return np.clip(out * 255, 0, 255).astype(np.uint8)


def eye_whites(frame, luma, pts, shape):
    """The white of each eye: the brighter pixels inside the eye opening, minus the iris and its reflection."""
    out = np.zeros(shape, np.float32)
    for eye, outline in zip(EYES, EYE_OUTLINE):
        opening = _eye_polygon(pts, outline, shape)
        opening = cv2.erode(opening, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        inside = opening > 0
        if inside.sum() < 30:
            continue
        centre = pts[eye["iris"][0]]
        radius = float(np.mean([np.hypot(*(pts[i] - centre)) for i in eye["iris"][1:]]))
        iris = np.zeros(shape, np.uint8)
        cv2.circle(iris, (int(centre[0]), int(centre[1])), int(radius * 1.3) + 1, 255, -1)
        white = inside & (iris == 0)
        if white.sum() < 20:
            continue
        threshold = np.percentile(luma[white], 45)
        gate = np.clip((luma - threshold) / 18, 0, 1) * white
        out = np.maximum(out, cv2.GaussianBlur(gate.astype(np.float32), (0, 0), 1.2))
    return np.clip(out * 255, 0, 255).astype(np.uint8)
