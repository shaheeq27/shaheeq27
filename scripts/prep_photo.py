#!/usr/bin/env python3
"""
prep_photo.py

Turns a normal photo into a grayscale, high-contrast, white-background
image that converts cleanly to ASCII art in make_ascii_svg.py.

Usage:
    python scripts/prep_photo.py source-photo.jpg

Output:
    source-prepped.png  (grayscale, white background, contrast-boosted)

Why each step exists:
  1. Background removal (rembg) - isolates the subject so the background
     doesn't turn into noisy ASCII characters.
  2. CLAHE contrast boost (OpenCV) - a flatly-lit face has very little
     local brightness variation, so it converts to a dark, muddy blob.
     CLAHE pulls out real highlights/shadows without blowing out the
     whole image the way a naive global contrast stretch would.
  3. White composite - matches the blank end of the ASCII ramp
     (a leading space in RAMP), so background = nothing printed.
"""

import sys
import io
from pathlib import Path

import numpy as np
import cv2
from PIL import Image

try:
    from rembg import remove as rembg_remove
    HAVE_REMBG = True
except ImportError:
    HAVE_REMBG = False


def remove_background(img: Image.Image) -> Image.Image:
    """Return an RGBA image with the background removed.

    Falls back to a no-op (returns the original image, alpha=255
    everywhere) if rembg isn't installed. rembg pulls a ~100MB ONNX
    model on first run, which needs network access to model hosting
    (not available in every environment) - so this fallback keeps
    the script usable for a quick contrast-only pass.
    """
    if not HAVE_REMBG:
        print(
            "[prep_photo] WARNING: rembg not available - skipping background "
            "removal. Install with `pip install rembg` and re-run for a clean "
            "cutout, or manually crop/mask your photo before running this "
            "script.",
            file=sys.stderr,
        )
        return img.convert("RGBA")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    out_bytes = rembg_remove(buf.getvalue())
    return Image.open(io.BytesIO(out_bytes)).convert("RGBA")


def clahe_boost(gray: np.ndarray) -> np.ndarray:
    """Apply contrast-limited adaptive histogram equalization.

    clipLimit=2.0 keeps noise amplification in check; tileGridSize=8x8
    is a reasonable default for face-sized subjects at typical webcam/
    portrait resolutions. Increase tileGridSize for higher-res source
    photos if local contrast still looks flat.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def composite_on_white(rgba: Image.Image) -> Image.Image:
    """Flatten an RGBA image onto a solid white background."""
    white_bg = Image.new("RGB", rgba.size, (255, 255, 255))
    white_bg.paste(rgba, mask=rgba.split()[3])  # alpha channel as mask
    return white_bg


def prep_photo(src_path: str, out_path: str = "source-prepped.png") -> None:
    src = Image.open(src_path).convert("RGB")

    cutout = remove_background(src)
    flattened = composite_on_white(cutout)

    gray = cv2.cvtColor(np.array(flattened), cv2.COLOR_RGB2GRAY)
    boosted = clahe_boost(gray)

    Image.fromarray(boosted).save(out_path)
    print(f"[prep_photo] wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/prep_photo.py <source-photo.jpg>", file=sys.stderr)
        sys.exit(1)

    src_arg = sys.argv[1]
    if not Path(src_arg).exists():
        print(f"[prep_photo] ERROR: {src_arg} not found", file=sys.stderr)
        sys.exit(1)

    prep_photo(src_arg)
