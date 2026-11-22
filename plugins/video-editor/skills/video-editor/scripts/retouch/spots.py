"""Freckles and small dark spots in close-ups, and the eyebrow's hairs, decided by the face's own size.

Why this exists: a close-up smooths skin twice (retouch.txt: a bilateral pass, then a stronger one). A bilateral filter
removes soft texture but keeps small, dark, high-contrast spots, so after two passes the freckles are the only texture
left and read as dirt ("little black stains around the eyebrow"). On the far side of a turned face the mask covers
less skin, so it looked fine. Two things follow:

  - brow_hair_keep: the eyebrow's hairs stay sharp, as before, but a freckle beside the brow is no longer taken for a
    hair. A hair is a dark stroke attached to the brow, or a long thin one; a small round blob apart from it is skin.
    The distances scale with the face's height, so a close-up is judged at its own size.
  - spot_mask: small, compact, dark spots on the skin (not moles, brows, eyes or lips) get a mask, and retouch.txt
    blends a median-smoothed copy through it, `spot_calm` (default 0.55) deep: the freckle stays, with about half its
    contrast, so the skin looks natural instead of plastic with dirt. 0 keeps spots as they are, 1 smooths them away.

Numpy and OpenCV only; mask.py calls these once per frame.
"""
import cv2
import numpy as np

REF_FACE = 600.0   # face height in pixels the brow distances (21, 5, 10) were tuned at
MOLE_DEPTH = 70.0  # a spot this much darker than the skin around it is a mole (or a pore in shadow): left alone


def _ellipse(size):
    size = max(1, int(size))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def _grow(canvas, size):
    return canvas if size <= 1 else cv2.dilate(canvas, _ellipse(size))


def brow_hair_keep(luma, brow_area, contrast, face_h=REF_FACE):
    """Float mask 0..1: the eyebrow's hairs, to leave unsmoothed.

    luma: float32 brightness; brow_area: uint8 (255 inside the brow outline); contrast: how much darker than its
    surroundings a pixel must be (settings brow_contrast); face_h: the face's height in pixels.
    Dark pixels in a band around the brow are candidates; a candidate patch is a hair only if it touches the brow
    outline or is a long thin stroke. Isolated compact blobs (freckles) are not kept."""
    scale = max(1.0, face_h / REF_FACE)
    zone = _grow(brow_area, int(round(21 * scale))) > 0
    darker = (cv2.GaussianBlur(luma, (0, 0), 10 * scale) - luma > contrast) & zone
    count, labels, stats, _ = cv2.connectedComponentsWithStats(darker.astype(np.uint8), connectivity=8)
    attached = _grow(brow_area, int(round(7 * scale))) > 0
    keep = np.zeros(luma.shape, np.uint8)
    for i in range(1, count):
        x, y, w, h, _area = stats[i]
        patch = labels[y:y + h, x:x + w] == i
        long_thin = max(w, h) >= 6 * scale and max(w, h) / max(1, min(w, h)) > 2.5
        if long_thin or attached[y:y + h, x:x + w][patch].any():
            keep[y:y + h, x:x + w][patch] = 255
    hair = _grow(keep, int(round(5 * scale)))
    return cv2.GaussianBlur(hair.astype(np.float32) / 255, (0, 0), 1.2 * scale)


def spot_mask(luma, skin, exclude, face_h, contrast=18.0):
    """Float mask 0..1 on small dark compact spots on the skin.

    luma: float32; skin: float 0..1 (where skin is softened); exclude: bool, True where a spot must be left alone
    (eyes, lips, mouth, the brow and its hairs); face_h: the face's height in pixels; contrast: how much darker than
    the skin around it a pixel must be (settings spot_contrast)."""
    face_h = max(float(face_h), 60.0)
    surround = cv2.GaussianBlur(luma, (0, 0), max(3.0, 0.025 * face_h))
    depth = surround - luma
    candidate = (depth > contrast) & (skin > 0.5) & ~exclude
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate.astype(np.uint8), connectivity=8)
    max_side = 0.026 * face_h          # about 18 px on a 700 px face: a big freckle
    result = np.zeros(luma.shape, np.uint8)
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        if area < 2 or max(w, h) > max_side or max(w, h) / max(1, min(w, h)) > 2.5 or area / float(w * h) < 0.35:
            continue                    # a speck, something big, a stroke (hair, lash) or a ragged shape
        patch = labels[y:y + h, x:x + w] == i
        if depth[y:y + h, x:x + w][patch].max() > MOLE_DEPTH:
            continue                    # a mole stays as it is
        result[y:y + h, x:x + w][patch] = 255
    result = _grow(result, max(3, int(round(0.006 * face_h))))
    soft = cv2.GaussianBlur(result.astype(np.float32) / 255, (0, 0), max(0.8, 0.003 * face_h))
    return np.clip(soft * 1.4, 0, 1) * (skin > 0.5) * (~exclude)
