"""The skin mask's outer edge, soft in proportion to the face's size.

The tracked face oval ends mid-forehead, and the mask used to fade out over a fixed 9 px. On a close-up the face is
750 px high or more, so 9 px is a razor edge: above it the forehead keeps its fine texture and baby hairs, below it the
skin is smooth (twice, in a close-up), and the line between them crawls as the head moves. Here the edge fades over
`feather` x the face height instead (default 0.04, about 30 px on a 750 px face); the eyes, lips and mouth keep
their own 9 px edges. Numpy and OpenCV only.
"""
import cv2
import numpy as np

EDGE_SIGMA = 9.0   # px: the fixed softness the mask always had


def soft_skin(base, tone, keep, face_h, feather):
    """Float 0..1 skin mask.

    base: float 0..1, the face area times the skin-colour gate; tone: float 0..1, the colour gate alone;
    keep: float 0..1, 0 where the eyes, lips, mouth (and brows, in margin mode) must stay untouched;
    face_h: the face's height in pixels; feather: the outer edge's softness as a share of face_h (0 = the old edge)."""
    sigma = float(feather) * float(face_h)
    if sigma <= EDGE_SIGMA:
        return cv2.GaussianBlur(base * keep, (0, 0), EDGE_SIGMA)
    outer = cv2.GaussianBlur(base, (0, 0), sigma)
    # the fade spreads outward too: not into pixels that aren't skin-coloured (hair, background)
    outer = np.minimum(outer, cv2.GaussianBlur(tone, (0, 0), EDGE_SIGMA))
    return outer * cv2.GaussianBlur(keep, (0, 0), EDGE_SIGMA)
