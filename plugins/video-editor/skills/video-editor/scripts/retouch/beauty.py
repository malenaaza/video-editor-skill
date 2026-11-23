"""Masks for the beautify extras: under-eye brightening and whiter eye whites.

Called by mask.py when those are on. No makeup and no reshaping: these only lift light a little, in
places the face tracker finds. Each mask is 0 to 255 and says where an effect applies; how strong it is
comes from the filter (beautify.py), so the same mask serves every level.
"""
import cv2
import numpy as np

import roi

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
        sigma = max(1.0, 0.1 * width)
        # the band, the eye and the blur's reach: a small box, not the whole frame (roi.py)
        b = roi.points_box(np.vstack([lid, down, pts[outline]]), 4 * sigma + 4, shape)
        if b is None:
            continue
        y0, y1, x0, x1 = b
        offset = np.array([x0, y0], np.float32)
        local, crop = pts - offset, (y1 - y0, x1 - x0)
        band = np.zeros(crop, np.uint8)
        cv2.fillPoly(band, [np.vstack([lid - offset, (down - offset)[::-1]]).astype(np.int32)], 255)
        band = band.astype(np.float32) / 255
        inside = _eye_polygon(local, outline, crop).astype(np.float32) / 255
        soft = cv2.GaussianBlur(band * (1 - inside), (0, 0), sigma)
        soft *= 1 - cv2.GaussianBlur(inside, (0, 0), 1.5)  # the soft edge must not leak into the eye
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], soft)
    return np.clip(out * 255, 0, 255).astype(np.uint8)


def eye_whites(frame, luma, pts, shape):
    """The white of each eye, all of it: the eye opening minus the iris and its reflection, kept away from the lashes.

    It used to be only the brighter half of the white, so a white with veins, spots or a shadow was lifted in patches
    and the rest stayed grey, which looked blotchy. Now the whole white is covered, so beautify.py can even it out
    (a median that removes veins and small spots) and whiten it in one piece; only pixels far darker than the white
    itself (lashes, the core of a shadow) are left out."""
    out = np.zeros(shape, np.float32)
    full_luma = luma
    for eye, outline in zip(EYES, EYE_OUTLINE):
        b = roi.points_box(pts[outline], 8, shape)   # the eye's box: a few percent of the frame (roi.py)
        if b is None:
            continue
        y0, y1, x0, x1 = b
        offset = np.array([x0, y0], np.float32)
        crop = (y1 - y0, x1 - x0)
        local = pts - offset
        luma = full_luma[y0:y1, x0:x1]
        opening = _eye_polygon(local, outline, crop)
        opening = cv2.erode(opening, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        inside = opening > 0
        if inside.sum() < 30:
            continue
        centre = pts[eye["iris"][0]]
        radius = float(np.mean([np.hypot(*(pts[i] - centre)) for i in eye["iris"][1:]]))
        iris = np.zeros(crop, np.uint8)
        cv2.circle(iris, (int(centre[0]) - x0, int(centre[1]) - y0), int(radius * 1.3) + 1, 255, -1)
        white = inside & (iris == 0)
        if white.sum() < 20:
            continue
        typical = float(np.median(luma[white]))
        gate = np.clip((luma - 0.5 * typical) / max(1.0, 0.12 * typical), 0, 1) * white
        out[y0:y1, x0:x1] = np.maximum(out[y0:y1, x0:x1], cv2.GaussianBlur(gate.astype(np.float32), (0, 0), 1.2))
    return np.clip(out * 255, 0, 255).astype(np.uint8)
