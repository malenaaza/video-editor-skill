"""Per-video settings for the retouch and blur scripts, read from retouch.json.

The scripts in this folder never need editing. Put a retouch.json in the folder you run them
from (the project's build folder) with only the values that differ from the defaults below:

  {"skin_cr_min": 132,
   "blur_keys": [{"name": "cardboard box", "lum": [106, null], "a": [2, 8], "b": [5, 19],
                  "hue": [9, 24], "sat": [null, 94]}]}

mask.py (skin and teeth):
  skin_strength   0 = no softening, 1 = full
  skin_cr_min     YCrCb red level where skin starts. Lower it if parts of the face are missing
                  from skin.mkv; raise it if hair or background is included.
  skin_cr_max     redder than this is clothing, not skin (a red top had about 224, skin 157-161)
  lips_cr_min     lips redder than this count as visible (teeth only whiten then)
  neck            also soften the neck under the jaw
  edge_faces      when the tracker finds no face, look for one cut in half by the frame edge
                  (see facetrack.py). On by default.
  edge_pad        share of the frame width mirrored for that search (0.5)
  close_lo, close_hi   face height as a share of the frame height where the extra close-up
                  softening starts and where it reaches full strength

blurmask.py and blurmask_hands.py (background blur):
  blur_skin       colour key for the speaker's skin, or null for each script's own default
  blur_keys       colour keys for things that must stay sharp: clothing, a held object.
                  Sample the object on a frame in Lab and HSV first; guessed values fail.
  blur_keys_below colour keys only count below this share of the frame height
                  (null = each script's own default: 0.42, or 0.45 with hands)
  hand_pad        pixels kept sharp around a tracked hand, for the product it holds
  hand_hold       frames to keep a hand after tracking loses it

A colour key is a set of ranges, all of which must match. Each range is [low, high], both
included, with null for no limit:
  lum 0..255, a and b -128..127 (Lab, as OpenCV gives them minus 128),
  hue 0..179, sat and val 0..255 (HSV, as OpenCV gives them).
A hue range with low above high wraps around red: "hue": [170, 7].
Examples: a red sweater  {"hue": [170, 7], "sat": [131, null], "val": [71, null], "a": [36, null]}
          a cardboard box {"lum": [106, null], "a": [2, 8], "b": [5, 19], "hue": [9, 24], "sat": [null, 94]}
"""
import json
import os
import sys

DEFAULTS = {
    "skin_strength": 0.88,
    "skin_cr_min": 139,
    "skin_cr_max": 185,
    "lips_cr_min": 146,
    "neck": True,
    "edge_faces": True,
    "edge_pad": 0.5,
    "close_lo": 0.31,
    "close_hi": 0.40,
    "blur_skin": None,
    "blur_keys": [],
    "blur_keys_below": None,
    "hand_pad": 60,
    "hand_hold": 6,
}
CHANNELS = ("lum", "a", "b", "hue", "sat", "val")


def check_key(key):
    for name, rng in key.items():
        if name == "name":
            continue
        if name not in CHANNELS:
            sys.exit(f"retouch.json: unknown colour channel {name!r}. Use: {', '.join(CHANNELS)}.")
        if not (isinstance(rng, list) and len(rng) == 2):
            sys.exit(f"retouch.json: {name} must be [low, high], with null for no limit.")


def load(path="retouch.json"):
    settings = dict(DEFAULTS)
    if os.path.exists(path):
        data = json.load(open(path, encoding="utf-8"))
        unknown = sorted(set(data) - set(DEFAULTS))
        if unknown:
            sys.exit(f"{path}: unknown settings {unknown}. Known: {sorted(DEFAULTS)}.")
        settings.update(data)
        for key in settings["blur_keys"] + ([settings["blur_skin"]] if settings["blur_skin"] else []):
            check_key(key)
        changed = {k: v for k, v in data.items() if v != DEFAULTS[k]}
        print(f"Settings from {path}: {json.dumps(changed, ensure_ascii=False)}", flush=True)
    else:
        print(f"No {path} here: using the default settings.", flush=True)
    return settings


def key_mask(frame, keys):
    """True where a BGR frame matches any of the colour keys."""
    import cv2
    import numpy as np

    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.int16)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.int16)
    planes = {"lum": lab[..., 0], "a": lab[..., 1] - 128, "b": lab[..., 2] - 128,
              "hue": hsv[..., 0], "sat": hsv[..., 1], "val": hsv[..., 2]}
    result = np.zeros(frame.shape[:2], bool)
    for key in keys:
        match = np.ones(frame.shape[:2], bool)
        for name, rng in key.items():
            if name == "name":
                continue
            low, high = rng
            plane = planes[name]
            if name == "hue" and low is not None and high is not None and low > high:
                match &= (plane >= low) | (plane <= high)
                continue
            if low is not None:
                match &= plane >= low
            if high is not None:
                match &= plane <= high
        result |= match
    return result
