"""Freckles and small dark spots in close-ups, and the eyebrow's hairs, decided by the face's own size.

Why this exists: a close-up smooths skin twice (retouch.txt: a bilateral pass, then a stronger one). A bilateral filter
removes soft texture but keeps small, dark, high-contrast spots, so after two passes the freckles are the only texture
left and read as dirt ("little black stains around the eyebrow"). On the far side of a turned face the mask covers
less skin, so it looked fine. Two things follow:

  - brow_hair_keep: the eyebrow's hairs stay sharp, as before, but a freckle beside the brow is no longer taken for a
    hair. A hair is a dark stroke attached to the brow, or a long thin one; a small round blob apart from it is skin.
    The distances scale with the face's height, so a close-up is judged at its own size.
  - spot_mask: small, compact, dark spots on the skin (not moles, brows, eyes or lips) get a mask, and retouch.txt
    blends a median-smoothed copy through it, `spot_calm` deep (0.55 roughly halves a freckle's contrast): the freckle stays, so the skin looks natural instead
    of plastic with dirt. Off by default (0): freckles are left as they are; 1 smooths them away.

Numpy and OpenCV only; mask.py calls these once per frame.
"""
import cv2
import numpy as np

import roi

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
    Dark pixels in a band around the brow are candidates; a candidate patch is a hair only if it lies mostly inside the
    brow outline, is a long thin stroke (a hair poking out, or stubble), or is an elongated stroke touching the
    outline. Compact blobs outside the outline, such as freckles or the grain of a shimmery lid right under the brow,
    are skin however close they are, and however big the face (the touching distance is not scaled: on a close-up it
    used to protect a band of skin 14-20 px wide under the brow)."""
    scale = max(1.0, face_h / REF_FACE)
    full = np.zeros(luma.shape, np.float32)
    # only the brows' box matters (the zone, the blur's reach and the final growth): work there (roi.py)
    b = roi.box(brow_area > 0, 21 * scale + 40 * scale + 5 * scale + 5 * scale + 4, luma.shape)
    if b is None:
        return full
    y0, y1, x0, x1 = b
    luma, brow_area = luma[y0:y1, x0:x1], brow_area[y0:y1, x0:x1]
    zone = _grow(brow_area, int(round(21 * scale))) > 0
    darker = (roi.blur(luma, 10 * scale) - luma > contrast) & zone
    count, labels, stats, _ = cv2.connectedComponentsWithStats(darker.astype(np.uint8), connectivity=8)
    inside = brow_area > 0
    attached = _grow(brow_area, 7) > 0
    keep = np.zeros(luma.shape, np.uint8)
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        patch = labels[y:y + h, x:x + w] == i
        aspect = max(w, h) / max(1, min(w, h))
        # a hair is thin: about 2 px wide at the reference size. A wide faint band (the grain of a shimmery lid under the
        # brow) can be as long and as elongated as a hair, but it is several times thicker.
        thin = area / float(max(w, h)) <= 2.0 * scale + 2
        stroke = thin and (aspect > 1.8 or area / float(w * h) < 0.6)   # elongated, or a thin diagonal line (a low fill)
        long_thin = thin and max(w, h) >= 6 * scale and aspect > 2.5
        in_brow = inside[y:y + h, x:x + w][patch].mean() >= 0.3
        touching = stroke and attached[y:y + h, x:x + w][patch].any()
        if long_thin or in_brow or touching:
            keep[y:y + h, x:x + w][patch] = 255
    hair = _grow(keep, int(round(5 * scale)))
    full[y0:y1, x0:x1] = cv2.GaussianBlur(hair.astype(np.float32) / 255, (0, 0), 1.2 * scale)
    return full


def spot_mask(luma, skin, exclude, face_h, contrast=14.0, bright=False):
    """Float mask 0..1 on small compact spots on the skin: dark ones (freckles), or with bright=True light ones
    (the glitter of a shimmery eyeshadow or highlighter, which a smoothing filter keeps as a patch of grain).

    luma: float32; skin: float 0..1 (where skin is softened); exclude: bool, True where a spot must be left alone
    (eyes, lips, mouth, the brow and its hairs); face_h: the face's height in pixels; contrast: how much darker (or,
    with bright, lighter) than the skin around it a pixel must be (settings spot_contrast, shimmer_contrast)."""
    face_h = max(float(face_h), 60.0)
    sigma = max(3.0, 0.025 * face_h)
    full = np.zeros(luma.shape, np.float32)
    # only the skin that may hold a spot, plus the surroundings' reach and the growth (roi.py)
    b = roi.box((skin > 0.5) & ~exclude, 4 * sigma + 0.006 * face_h + 4 * 0.003 * face_h + 6, luma.shape)
    if b is None:
        return full
    y0, y1, x0, x1 = b
    luma, skin, exclude = luma[y0:y1, x0:x1], skin[y0:y1, x0:x1], exclude[y0:y1, x0:x1]
    surround = roi.blur(luma, sigma)
    depth = (luma - surround) if bright else (surround - luma)
    candidate = ((depth > contrast) & (skin > 0.5) & ~exclude).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
    max_side = 0.026 * face_h          # about 18 px on a 700 px face: a big freckle
    result = np.zeros(luma.shape, np.uint8)
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        if area < 2 or max(w, h) > max_side or max(w, h) / max(1, min(w, h)) > 2.5 or area / float(w * h) < 0.35:
            continue                    # a speck, something big, a stroke (hair, lash) or a ragged shape
        patch = labels[y:y + h, x:x + w] == i
        if depth[y:y + h, x:x + w][patch].max() > MOLE_DEPTH:
            continue                    # a mole (or, bright, a real reflection) stays as it is
        result[y:y + h, x:x + w][patch] = 255
    result = _grow(result, max(3, int(round(0.006 * face_h))))
    soft = cv2.GaussianBlur(result.astype(np.float32) / 255, (0, 0), max(0.8, 0.003 * face_h))
    full[y0:y1, x0:x1] = np.clip(soft * 1.4, 0, 1) * (skin > 0.5) * (~exclude)
    return full
