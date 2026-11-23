"""The skin mask's outer edge, soft in proportion to the face's size.

The tracked face oval ends mid-forehead, and the mask used to fade out over a fixed 9 px. On a close-up the face is
750 px high or more, so 9 px is a razor edge: above it the forehead keeps its fine texture and baby hairs, below it the
skin is smooth (twice, in a close-up), and the line between them crawls as the head moves. Here the edge fades over
`feather` x the face height instead (default 0.04, about 30 px on a 750 px face); the eyes, lips and mouth keep
their own 9 px edges. Numpy and OpenCV only.
"""
import cv2
import numpy as np

import roi

EDGE_SIGMA = 9.0   # px: the fixed softness the mask always had


def soft_skin(base, tone, keep, face_h, feather):
    """Float 0..1 skin mask.

    base: float 0..1, the face area times the skin-colour gate; tone: float 0..1, the colour gate alone;
    keep: float 0..1, 0 where the eyes, lips, mouth (and brows, in margin mode) must stay untouched;
    face_h: the face's height in pixels; feather: the outer edge's softness as a share of face_h (0 = the old edge)."""
    sigma = float(feather) * float(face_h)
    wide = sigma > EDGE_SIGMA
    out = np.zeros(base.shape, np.float32)
    # Only the face's box (plus the blur's reach) can be non-zero, and the wide blur is done on a smaller copy:
    # the same mask, several times faster on a close-up (roi.py).
    b = roi.box(base > 0, 4 * (sigma if wide else EDGE_SIGMA) + 2, base.shape)
    if b is None:
        return out
    y0, y1, x0, x1 = b
    base, tone, keep = base[y0:y1, x0:x1], tone[y0:y1, x0:x1], keep[y0:y1, x0:x1]
    if not wide:
        out[y0:y1, x0:x1] = cv2.GaussianBlur(base * keep, (0, 0), EDGE_SIGMA)
        return out
    outer = roi.blur(base, sigma)
    # the fade spreads outward too: not into pixels that aren't skin-coloured (hair, background)
    outer = np.minimum(outer, cv2.GaussianBlur(tone, (0, 0), EDGE_SIGMA))
    out[y0:y1, x0:x1] = outer * cv2.GaussianBlur(keep, (0, 0), EDGE_SIGMA)
    return out
