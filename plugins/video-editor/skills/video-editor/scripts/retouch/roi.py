"""Speed helpers for mask.py: work only in the box that matters, and blur widely on a smaller copy.

A mask of a 1080x1920 frame is mostly empty: the face, and inside it the eyes or the brows, are a part of it. And a
Gaussian blur with a wide sigma (the forehead fade, the "surroundings" a spot is compared with) costs time in
proportion to sigma, but a wide blur loses nothing when it is done on a copy shrunk by about sigma / 8 and enlarged
again. Used by feather.py, spots.py and beauty.py; their masks stay the same within a level or two out of 255.
Numpy and OpenCV only.
"""
import cv2
import numpy as np

SHRINK_FROM = 8.0   # sigma (px) from which a blur is done on a smaller copy
FAST = True         # False: whole frame, plain blurs (the reference the tests compare with)


def box(mask, margin, shape):
    """(y0, y1, x0, x1): the bounding box of the mask's non-zero pixels plus margin, inside the frame; None if empty."""
    m = np.ascontiguousarray(mask).astype(np.uint8)
    x, y, w, h = cv2.boundingRect(m)
    if w == 0 or h == 0:
        return None
    if not FAST:
        return (0, shape[0], 0, shape[1])
    margin = int(np.ceil(margin))
    return (max(0, y - margin), min(shape[0], y + h + margin), max(0, x - margin), min(shape[1], x + w + margin))


def points_box(points, margin, shape):
    """(y0, y1, x0, x1) around a set of (x, y) points plus margin, inside the frame; None if nothing is left."""
    if not FAST:
        return (0, shape[0], 0, shape[1])
    p = np.asarray(points, np.float32).reshape(-1, 2)
    margin = int(np.ceil(margin))
    y0, y1 = max(0, int(np.floor(p[:, 1].min())) - margin), min(shape[0], int(np.ceil(p[:, 1].max())) + margin + 1)
    x0, x1 = max(0, int(np.floor(p[:, 0].min())) - margin), min(shape[1], int(np.ceil(p[:, 0].max())) + margin + 1)
    return (y0, y1, x0, x1) if y1 > y0 and x1 > x0 else None


def blur(img, sigma):
    """cv2.GaussianBlur(img, (0, 0), sigma), done on a smaller copy when sigma is wide."""
    h, w = img.shape[:2]
    k = int(round(sigma / SHRINK_FROM))
    if not FAST or sigma < SHRINK_FROM or k < 2 or min(h, w) < 8 * k:
        return cv2.GaussianBlur(img, (0, 0), sigma)
    sw, sh = max(1, int(round(w / k))), max(1, int(round(h / k)))
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigmaX=sigma * sw / w, sigmaY=sigma * sh / h)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
