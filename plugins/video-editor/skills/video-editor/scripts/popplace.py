"""Where a product pop-in goes: beside the speaker's temple, never over the product in their hand.

  <face python> -I popplace.py <frame.png> <face_landmarker.task> [--hands <hand_landmarker.task>]
                               [--image product.png | --clip] [--size 300] [--label] [--caption-top 1320]

Give it the frame of the video where the pop-in starts. It finds the face (MediaPipe face landmarks, with the
EdgeFace fallback for a face cut by the frame edge) and, with --hands, the hands. The pop-in is centred at temple
height, right beside the face, on the side with more room. A hand, and the product it holds (an area reaching well
above the fingers), is never covered: if they are in the way, it tries a smaller size lifted above them, then the
other side, and says what it did. It shrinks to fit a narrow strip (down to 18% of the frame width) and keeps the
whole pop-in, label included, above the caption area. If nothing fits, it says to skip the pop-in. It prints the
ProductPop props to copy into the props file: side, margin, top, size.
"""
import argparse
import json
import os
import sys

OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176,
        149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
TEMPLES = (127, 356)  # beside the eyes, at the temples


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def hand_zone(points, width, height):
    """A hand's box, grown to cover the product it holds (products stick out above and beside the fingers)."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    size = max(w, h)
    return (max(0, min(xs) - 0.6 * size), max(0, min(ys) - 1.6 * size), min(width, max(xs) + 0.6 * size),
            min(height, max(ys) + 0.4 * size))


def place(face, hands, width, height, aspect, size=None, gap=None, label=False, caption_top=None):
    """face: dict with left, right, top (forehead), temple_y. hands: list of boxes. aspect: height / width of the
    picture. Returns the ProductPop props and notes."""
    size = size or round(0.30 * width)
    gap = gap if gap is not None else round(0.03 * width)
    edge = round(0.025 * width)
    floor = caption_top if caption_top else round(0.70 * height)
    label_h = round(0.07 * height) if label else 0
    notes = []
    ceiling = round(0.04 * height)
    smallest = 0.18 * width
    sides = sorted(("left", "right"), key=lambda s: -(face["left"] if s == "left" else width - face["right"]))
    for side in sides:  # the side with more room first
        room = (face["left"] if side == "left" else width - face["right"]) - gap - edge
        for wanted in (size, 0.85 * size, 0.7 * size, smallest):
            s = min(wanted, room)
            if s < smallest - 0.5:
                continue
            h = s * aspect
            total = h + label_h
            x = face["left"] - gap - s if side == "left" else face["right"] + gap
            top = max(ceiling, min(face["temple_y"] - h / 2, floor - total))  # centred at the temples
            box = (x, top, x + s, top + total)
            lifted = False
            blocking = [z for z in hands if overlaps(box, z)]
            if blocking:  # lift it above the hand and the product, if there's room up there
                top = min(z[1] for z in blocking) - total - gap
                box = (x, top, x + s, top + total)
                lifted = True
                if top < ceiling or any(overlaps(box, z) for z in hands):
                    continue
            if s < size:
                notes.append(f"made smaller to fit ({round(s)} px instead of {size})")
            if lifted:
                notes.append("lifted above the hand and the product it holds")
            if side != sides[0]:
                notes.append("put on the side with less room: the other side had a hand or the product")
            margin = round(x if side == "left" else width - (x + s))
            return {"side": side, "margin": margin, "top": round(top), "size": round(s)}, notes
    if label:  # a picture without its name may still fit
        props, more = place(face, hands, width, height, aspect, size, gap, label=False, caption_top=caption_top)
        if props:
            props["name"] = None
            return props, more + ["the name under the picture was left out: there's no room for it here"]
    return None, ["no room beside the head that doesn't cover the face, a hand or the product: skip this pop-in, "
                  "or use a smaller product tag"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("frame")
    ap.add_argument("face_model")
    ap.add_argument("--hands", help="hand_landmarker.task, to keep the product in the hand uncovered")
    ap.add_argument("--image", help="the product picture, to read its shape")
    ap.add_argument("--clip", action="store_true", help="a clip card (9:16)")
    ap.add_argument("--size", type=int, help="wanted width in pixels (default 30%% of the frame width)")
    ap.add_argument("--label", action="store_true", help="the pop-in shows a name under the picture")
    ap.add_argument("--caption-top", type=int, help="where the caption area starts (my-setup.md)")
    a = ap.parse_args()

    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, HandLandmarker, HandLandmarkerOptions

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "retouch"))
    from facetrack import EdgeFace

    frame = cv2.imread(a.frame)
    if frame is None:
        sys.exit(f"Can't read {a.frame}")
    height, width = frame.shape[:2]
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    with FaceLandmarker.create_from_options(FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=a.face_model),
                                                                  num_faces=1)) as lm:
        found = lm.detect(image).face_landmarks
    if found:
        pts = [(p.x * width, p.y * height) for p in found[0]]
    else:
        edge = EdgeFace(a.face_model)
        points = edge.detect(frame)
        edge.close()
        if points is None:
            sys.exit("No face found in this frame: pick a frame a moment later, or place it by eye.")
        pts = [tuple(p) for p in points]
    oval = [pts[i] for i in OVAL]
    face = {"left": max(0, min(p[0] for p in oval)), "right": min(width, max(p[0] for p in oval)),
            "top": pts[10][1], "temple_y": sum(pts[i][1] for i in TEMPLES) / 2}
    hands = []
    if a.hands:
        with HandLandmarker.create_from_options(HandLandmarkerOptions(base_options=BaseOptions(model_asset_path=a.hands),
                                                                      num_hands=2, min_hand_detection_confidence=0.4)) as hl:
            for hand in hl.detect(image).hand_landmarks:
                hands.append(hand_zone([(p.x * width, p.y * height) for p in hand], width, height))
    if a.clip:
        aspect = 16 / 9
    elif a.image:
        picture = cv2.imread(a.image, cv2.IMREAD_UNCHANGED)
        aspect = picture.shape[0] / picture.shape[1] if picture is not None else 1.2
    else:
        aspect = 1.2
    props, notes = place(face, hands, width, height, aspect, a.size, label=a.label, caption_top=a.caption_top)
    print(f"Face from x {face['left']:.0f} to {face['right']:.0f}, temples at y {face['temple_y']:.0f}; "
          f"{len(hands)} hand(s) found" + ("" if a.hands else " (no --hands: the product in the hand isn't checked)"))
    for note in notes:
        print("Note:", note)
    if props:
        print(json.dumps(props))


if __name__ == "__main__":
    main()
