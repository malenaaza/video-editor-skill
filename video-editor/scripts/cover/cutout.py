"""Cut a product out of a photo or a video frame, for the cover.

Usage:
  python -I cutout.py <image> <out.png> [--crop x,y,w,h] [--white] [--pad 24] [--check check.png]

  --crop   cut out only this box (pixels), e.g. the product in a video frame,
           so the speaker and the room aren't picked up.
  --white  for shop photos on a plain light background, including white boxes and white
           products: it finds the product's outline (its edge and shadow) against the
           background color and fills everything inside it. No model needed.
  --pad    transparent margin around the trimmed product, in pixels.
  --check  also save a check image: the cutout over red and over black, where any part
           that turned see-through shows at once. Look at it before using the cutout.

Without --white it uses rembg (isnet-general-use model, downloaded on first use), best for
video frames and busy backgrounds.
Either way, the inside of the product is then made solid, so white parts can't turn
see-through and show the cover's background, and loose specks are removed.
The output is a transparent PNG trimmed to the product. It prints how much of the image is
kept: a very small or very large share usually means the cutout failed.
"""
import argparse
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


def fill_holes(mask: Image.Image) -> Image.Image:
    """Make every area the outside can't reach part of the product (L mode, 255 = product)."""
    outside = ImageChops.invert(mask).copy()
    w, h = outside.size
    border = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    for point in border:
        if outside.getpixel(point) == 255:
            ImageDraw.floodfill(outside, point, 128)
    return Image.fromarray(np.where(np.asarray(outside) == 128, 0, 255).astype(np.uint8))


def keep_large_parts(mask: Image.Image, share: float = 0.02) -> Image.Image:
    """Drop loose specks: parts smaller than this share of the biggest part."""
    try:
        from scipy import ndimage
    except ImportError:
        return mask
    solid = np.asarray(mask) > 127
    labels, count = ndimage.label(solid)
    if count <= 1:
        return mask
    sizes = ndimage.sum(solid, labels, range(1, count + 1))
    keep = np.isin(labels, 1 + np.flatnonzero(sizes >= sizes.max() * share))
    return Image.fromarray(np.where(keep, 255, 0).astype(np.uint8))


def solidify(mask: Image.Image) -> Image.Image:
    """Close small gaps in the outline, fill the inside, remove specks, soften the edge."""
    w, h = mask.size
    k = max(3, (min(w, h) // 150) | 1)  # about 0.7% of the image, odd
    mask = mask.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))  # close gaps
    mask = fill_holes(mask)
    mask = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))  # remove thin specks
    mask = keep_large_parts(mask)
    # Pull the edge in by a pixel to drop the background fringe, then soften it.
    return mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))


def white_cutout(img: Image.Image) -> Image.Image:
    """Shop photo on a light background: the product is whatever differs from that color."""
    rgb = img.convert("RGB")
    a = np.asarray(rgb.filter(ImageFilter.GaussianBlur(1.0))).astype(np.int16)
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    background = np.median(border, axis=0)
    diff = np.abs(a - background).max(axis=2)
    noise = np.percentile(np.abs(border - background).max(axis=1), 99)
    mask = Image.fromarray(np.where(diff > max(6, noise + 3), 255, 0).astype(np.uint8))
    out = rgb.convert("RGBA")
    out.putalpha(solidify(mask))
    return out


def model_cutout(img: Image.Image) -> Image.Image:
    from rembg import new_session, remove

    session = new_session("isnet-general-use")
    cut = remove(img.convert("RGB"), session=session)
    # The model leaves white and pale parts partly see-through: make the inside solid.
    mask = cut.getchannel("A").point(lambda v: 255 if v > 24 else 0)
    out = img.convert("RGBA")
    out.putalpha(solidify(mask))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--crop", help="x,y,w,h in pixels")
    ap.add_argument("--white", action="store_true")
    ap.add_argument("--pad", type=int, default=24)
    ap.add_argument("--check", help="also save the cutout over red and black here")
    args = ap.parse_args()

    img = Image.open(args.image)
    img.load()
    if args.crop:
        x, y, w, h = (int(v) for v in args.crop.split(","))
        img = img.crop((x, y, x + w, y + h))

    out = white_cutout(img) if args.white else model_cutout(img)

    alpha = np.asarray(out.getchannel("A"))
    kept = float((alpha > 128).mean())
    box = out.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if box is None:
        print("Nothing was kept: the cutout failed. Try the other mode or a tighter --crop.")
        return 1
    out = out.crop(box)
    padded = Image.new("RGBA", (out.width + 2 * args.pad, out.height + 2 * args.pad), (0, 0, 0, 0))
    padded.paste(out, (args.pad, args.pad))
    padded.save(args.out)
    if args.check:
        tiles = Image.new("RGB", (padded.width * 2 + 20, padded.height), "white")
        for i, color in enumerate([(200, 20, 30), (20, 20, 20)]):
            tile = Image.new("RGB", padded.size, color)
            tile.paste(padded, (0, 0), padded)
            tiles.paste(tile, (i * (padded.width + 20), 0))
        tiles.save(args.check)

    print(f"Saved {args.out} ({padded.width}x{padded.height}), kept {kept:.0%} of the image.")
    if kept < 0.03 or kept > 0.9:
        print("That share looks wrong for a product: check the cutout before using it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
