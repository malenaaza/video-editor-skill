"""The area kept sharp around a hand that holds a product, for blurmask_hands.py.

A product sticks out of the hand along the direction the hand holds it: from the wrist, past the knuckles and the
fingers (a lipstick or serum cap held up, a bottle's top). A ring of the same size all round the hand blurred the far
end of the product: with 60 px, 72% of a serum's cap; with 120 px, up to 9% of it. So the zone is the hand's outline
swept along that direction by `reach` times the hand's length, then grown by `pad` pixels on every side.
While tracking has lost the hand (`missing` frames), the zone grows by `grow_lost` pixels a frame, because the hand
may have moved.
"""
import cv2
import numpy as np

WRIST, MIDDLE_KNUCKLE = 0, 9


def hand_keep(points, shape, pad=120, reach=0.4, missing=0, grow_lost=12):
    """A uint8 mask (255 = keep sharp) for one hand. points: the 21 hand landmarks in pixels."""
    points = np.asarray(points, np.float32)
    axis = points[MIDDLE_KNUCKLE] - points[WRIST]
    length = float(np.linalg.norm(axis))
    hull = cv2.convexHull(points)[:, 0, :]
    if length > 1:
        span = np.ptp(points, axis=0).max()
        shift = axis / length * reach * max(length, span)
        hull = cv2.convexHull(np.vstack([hull, hull + shift]).astype(np.float32))[:, 0, :]
    zone = np.zeros(shape, np.uint8)
    cv2.fillConvexPoly(zone, hull.astype(np.int32), 255)
    grow = int(pad + missing * grow_lost)
    if grow > 0:
        zone = cv2.dilate(zone, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1)))
    return zone
