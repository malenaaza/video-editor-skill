"""Finds a face that the frame edge cuts in half, which the normal face tracker misses.

MediaPipe's face landmarker finds nothing when a close-up crops the face at the side of the frame
(the speaker leans in, or a punch-in zoom pushes half the face out). Without landmarks the
skin mask is empty and the skin comes out unsoftened, and the background blur can't see the head.

The fix: when the tracker finds no face, paste a mirror image of the visible part next to the
frame edge, which makes a whole, symmetric face, run the (stateless) tracker on that, and map the
points back. Tried on a real close-up with half a face in frame: no face on the plain frame, and a
face whose oval covered the visible cheek, jaw and neck once mirrored. Half a frame width of
mirror worked better than a whole one. The landmarks of the cut-off half are invented, so they
describe the visible half's size and position but not the hidden half; nothing is drawn there.

A detection is accepted only if the face's centre (the nose tip) lands near the edge it was mirrored
across, so a face-free frame that happens to mirror into a face-like pattern is not taken.

Settings (retouch.json, see settings.py): edge_faces (true/false), edge_pad (share of the frame
width that is mirrored, 0.5).
"""
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

NOSE = 1


def mirrored(frame, side, pad_px):
    """The frame with a mirror image of its `side` edge pasted outside that edge."""
    if side == "right":
        return np.hstack([frame, frame[:, -pad_px:][:, ::-1]])
    return np.hstack([frame[:, :pad_px][:, ::-1], frame])


def plausible(points, width, side, pad_px):
    """True if the face centre is near the edge it was mirrored across (points in padded pixels)."""
    x = points[NOSE][0] - (pad_px if side == "left" else 0)  # to frame coordinates
    near = x >= 0.6 * width if side == "right" else x <= 0.4 * width
    return bool(near and -0.5 * width <= x <= 1.5 * width)


class EdgeFace:
    def __init__(self, model_path, enabled=True, pad=0.5):
        self.enabled = enabled
        self.pad = pad
        self.found = 0
        self._landmarker = None
        if enabled:
            options = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=model_path),
                                            running_mode=RunningMode.IMAGE, num_faces=1)
            self._landmarker = FaceLandmarker.create_from_options(options)

    def close(self):
        if self._landmarker:
            self._landmarker.close()

    def detect(self, frame):
        """Landmarks, in pixels of `frame` (a BGR image), or None. Points can lie outside the frame."""
        if not self.enabled:
            return None
        import cv2

        height, width = frame.shape[:2]
        pad_px = max(int(width * self.pad), 16)
        for side in ("right", "left"):
            padded = np.ascontiguousarray(mirrored(frame, side, pad_px))
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(padded, cv2.COLOR_BGR2RGB))
            result = self._landmarker.detect(image)
            if not result.face_landmarks:
                continue
            points = np.array([[p.x * padded.shape[1], p.y * padded.shape[0]] for p in result.face_landmarks[0]],
                              np.float32)
            if not plausible(points, width, side, pad_px):
                continue
            if side == "left":
                points[:, 0] -= pad_px
            self.found += 1
            return points
        return None
