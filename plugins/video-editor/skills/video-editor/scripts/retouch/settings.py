"""Per-video settings for the retouch and blur scripts, read from retouch.json.

The scripts in this folder never need editing. Put a retouch.json in the folder you run them
from (the project's build folder) with only the values that differ from the defaults below:

  {"skin_cr_min": 132,
   "blur_keys": [{"name": "cardboard box", "lum": [106, null], "a": [2, 8], "b": [5, 19],
                  "hue": [9, 24], "sat": [null, 94]}]}

mask.py (skin and teeth):
  beautify        "off" (default), "light", "medium" or "strong": one setting that sets the skin
                  softening and the three extras below together (see PRESETS). Anything you also
                  write in retouch.json wins over the preset. No makeup and no reshaping, ever.
  glow            a soft lift of the skin's brightness through the skin mask, keeping its colour (0 = off, 0.02 is gentle)
  under_eye       brightens the band under each eye, where dark circles sit (0 = off, 0.045 is gentle)
  eye_white       brightens and de-reddens the white of each eye (0 = off, 0.09 is gentle)
  skin_strength   0 = no softening, 1 = full
  skin_cr_min     YCrCb red level where skin starts. Lower it if parts of the face are missing
                  from skin.mkv; raise it if hair or background is included.
  skin_cr_max     redder than this is clothing, not skin (a red top had about 224, skin 157-161)
  lips_cr_min     lips redder than this count as visible (teeth only whiten then)
  neck            also soften the neck under the jaw
  region_grow     [x, y] how far beyond the tracker's face outline to look for skin, as a multiple
                  of the outline (default [1.35, 1.1]). On a turned face the outline of the far
                  cheek lies well inside the real cheek; skin-coloured pixels that touch the face
                  inside this wider area are softened too. [1, 1] switches it off.
  brow_mode       "hair" (default): protect only the dark brow hairs, so the skin between and
                  around them is smoothed like the rest of the face. "margin": leave a margin of
                  protect_brows pixels around the whole brow, as the eyes and lips have.
  brow_contrast   how much darker than its surroundings a pixel must be to count as brow hair
                  in "hair" mode (luma levels, default 14). Lower it if fine or pale hairs get
                  smoothed; raise it if skin texture near the brows is being kept.
  protect_brows   the margin in pixels for brow_mode "margin" (default 15)
  protect_eyes    the margin in pixels around the eyes (default 15). Lips and mouth keep 25.
  crown           null, or {"grow": [1.45, 1.30], "raise": 0.36}: also keep sharp an area above the head
                  (hair, a tall headband, a hat): the face outline scaled by grow around its centre and
                  raised by raise times the face height. A braided headband above the hairline was
                  being blurred with the default head area.
  edge_faces      when the tracker finds no face, look for one cut in half by the frame edge
                  (see facetrack.py). On by default.
  edge_pad        share of the frame width mirrored for that search (0.5)
  spot_calm       how much contrast freckles and other small dark spots on the skin lose: 0 keeps them as they
                  are (default: freckles are part of a face and the skill leaves them), 1 smooths them away, 0.55 roughly halves
                  it. A close-up smooths the skin twice, and a smoothing filter keeps small dark spots, so for
                  someone whose freckles then read as dirt, 0.55 calms them. Moles (bigger and much darker), eyes, lips and brows are never touched.
  spot_contrast   how much darker than the skin around it a pixel must be to count as a spot (default 14)
  shimmer_calm    how much contrast small bright specks on the skin lose (the glitter of a shimmery eyeshadow or
                  highlighter, or a dry or bumpy patch of skin), which the smoothing keeps as a patch of grain next to smooth skin: 0 leaves it as it is,
                  1 smooths it away, 0.6 (default) calms it and the sparkle stays. Real reflections, eyes, lips and
                  brows are never touched.
  shimmer_contrast  how much lighter than the skin around it a pixel must be to count as a speck (default 8)
  forehead_feather  how softly the skin mask fades at its outer edge (the forehead's top, the jaw), as a share of the
                  face's height: 0.04 (default) is about 30 px on a 750 px face; 0 is the old fixed 9 px edge. The
                  tracked face outline ends mid-forehead, and a hard edge there showed as a line between smooth skin
                  and textured skin that crawled as the head moved. Raise it to 0.07 if a line is still visible.
  close_lo, close_hi   face height as a share of the frame height where the extra close-up
                  softening starts and where it reaches full strength

blurmask.py and blurmask_hands.py (background blur):
  blur_skin       colour key for the speaker's skin, or null for each script's own default
  blur_keys       colour keys for things that must stay sharp: clothing, a held object.
                  Sample the object on a frame in Lab and HSV first; guessed values fail.
  blur_keys_below colour keys only count below this share of the frame height
                  (null = each script's own default: 0.42, or 0.45 with hands)
  hand_pad        pixels kept sharp around a tracked hand, for the product it holds (default 120,
                  counted on the half-size frame the mask is built on; 60 blurred 72% of a serum's cap
                  held up above the fingers)
  hand_reach      how far the sharp area also stretches past the fingers, in hand lengths, along the
                  direction the hand holds the product (wrist to knuckles; default 0.4). With the ring
                  alone, up to 9% of that cap still blurred; with 0.4, none of it after the first frame,
                  and 19% of the frame was still blurred background instead of 23%. Raise it for long
                  products, lower it if too much background stays sharp.
  hand_hold       frames to keep a hand after tracking loses it (default 10); the kept area grows
                  while it's lost, because the hand may have moved

pixelfaces.py (pixelating the faces of other people):
  pixel_keep      null (default: only the speaker, the face seen most, stays sharp) or a list of track
                  numbers to leave sharp, as printed by `pixelfaces.py scan`. Use it when the speaker was
                  split into two tracks, or when a second person should stay visible.
  pixel_extra     faces the detector misses (small, in profile, turned away): a list of
                  {"start": seconds, "end": seconds, "box": [x, y, width, height]} in pixels of the video.
  pixel_margin    how much is added on every side of a face, as a share of its size (0.35; the top gets
                  0.15 more for hair and forehead)
  pixel_block     size in pixels of the squares, or null: a seventh of the largest pixelated face, so a
                  face is never more than about 7 squares wide and smaller ones are a single blur
  pixel_gap       seconds of missed detections that are bridged by moving the box between the last and
                  next sighting (1.5)
  pixel_hold      seconds the box stays before the first and after the last sighting (0.4), because the
                  face is on screen before and after the detector notices it
  pixel_faces     most faces the detector looks for in a frame (6)

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

PRESETS = {
    "light": {"skin_strength": 0.55, "close_lo": 0.38, "close_hi": 0.52, "glow": 0.012, "under_eye": 0.025, "eye_white": 0.05},
    "medium": {"skin_strength": 0.72, "close_lo": 0.34, "close_hi": 0.46, "glow": 0.022, "under_eye": 0.045, "eye_white": 0.09},
    "strong": {"skin_strength": 0.88, "close_lo": 0.31, "close_hi": 0.40, "glow": 0.035, "under_eye": 0.065, "eye_white": 0.13},
}

DEFAULTS = {
    "beautify": "off",
    "glow": 0.0,
    "under_eye": 0.0,
    "eye_white": 0.0,
    "skin_strength": 0.88,
    "skin_cr_min": 139,
    "skin_cr_max": 185,
    "lips_cr_min": 146,
    "neck": True,
    "region_grow": [1.35, 1.1],
    "brow_mode": "hair",
    "brow_contrast": 14,
    "protect_brows": 15,
    "protect_eyes": 15,
    "crown": None,
    "edge_faces": True,
    "edge_pad": 0.5,
    "close_lo": 0.31,
    "close_hi": 0.40,
    "blur_skin": None,
    "blur_keys": [],
    "blur_keys_below": None,
    "hand_pad": 120,
    "hand_reach": 0.4,
    "hand_hold": 10,
    "pixel_keep": None,
    "pixel_extra": [],
    "pixel_margin": 0.35,
    "pixel_block": None,
    "pixel_gap": 1.5,
    "pixel_hold": 0.4,
    "pixel_faces": 6,
    "spot_calm": 0,
    "spot_contrast": 14,
    "shimmer_calm": 0.6,
    "shimmer_contrast": 8,
    "forehead_feather": 0.04,
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
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        unknown = sorted(set(data) - set(DEFAULTS))
        if unknown:
            sys.exit(f"{path}: unknown settings {unknown}. Known: {sorted(DEFAULTS)}.")
        preset = data.get("beautify", "off")
        if preset != "off":
            if preset not in PRESETS:
                sys.exit(f'{path}: beautify must be "off", "light", "medium" or "strong", not {preset!r}.')
            settings.update(PRESETS[preset])  # explicit settings in the file win over the preset
        settings.update(data)
        for key in settings["blur_keys"] + ([settings["blur_skin"]] if settings["blur_skin"] else []):
            check_key(key)
        if not (isinstance(settings["spot_calm"], (int, float)) and 0 <= settings["spot_calm"] <= 1):
            sys.exit("retouch.json: spot_calm must be a number from 0 (keep spots as they are) to 1 (smooth them away).")
        if not (isinstance(settings["forehead_feather"], (int, float)) and 0 <= settings["forehead_feather"] <= 0.2):
            sys.exit("retouch.json: forehead_feather must be a number from 0 (a hard edge) to 0.2 (a very soft one).")
        if not (isinstance(settings["shimmer_calm"], (int, float)) and 0 <= settings["shimmer_calm"] <= 1):
            sys.exit("retouch.json: shimmer_calm must be a number from 0 (keep the glitter as it is) to 1 (smooth it away).")
        crown = settings["crown"]
        if crown is not None and not (isinstance(crown, dict) and len(crown.get("grow", [])) == 2 and "raise" in crown):
            sys.exit('retouch.json: crown must be {"grow": [x, y], "raise": number}, for example '
                     '{"grow": [1.45, 1.30], "raise": 0.36}.')
        for extra in settings["pixel_extra"]:
            box = extra.get("box") if isinstance(extra, dict) else None
            if not (isinstance(box, list) and len(box) == 4 and "start" in extra and "end" in extra):
                sys.exit('retouch.json: each pixel_extra must be {"start": s, "end": s, "box": [x, y, width, height]}.')
        keep = settings["pixel_keep"]
        if keep is not None and not (isinstance(keep, list) and all(isinstance(k, int) for k in keep)):
            sys.exit("retouch.json: pixel_keep must be null or a list of track numbers, for example [0, 2].")
        changed = {k: v for k, v in settings.items() if v != DEFAULTS[k]}
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
