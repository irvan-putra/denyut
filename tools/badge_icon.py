#!/usr/bin/env python3
"""Generate denyut launcher icons with the version badged on the icon.

A pulse line (the app name means "pulse") on a dark teal field, with the
version inside the lower safe area. Deterministic from the version string.
Usage: tools/badge_icon.py 0.6.4   (requires Pillow)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
BG = (16, 52, 56, 255)
LINE = (120, 230, 200, 255)
STRIP = (8, 28, 30, 215)
TEXT = (235, 250, 245, 255)


def render(size, version):
    img = Image.new("RGBA", (size, size), BG)
    d = ImageDraw.Draw(img)
    # pulse polyline across the upper two thirds
    pts = [(0.14, 0.42), (0.34, 0.42), (0.42, 0.22), (0.54, 0.62), (0.62, 0.42), (0.86, 0.42)]
    xy = [(x * size, y * size) for x, y in pts]
    w = max(2, int(size * 0.055))
    d.line(xy, fill=LINE, width=w, joint="curve")
    for x, y in (xy[0], xy[-1]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=LINE)
    strip_h = int(size * 0.18)
    y0 = size - strip_h - int(size * 0.06)
    d.rectangle([0, y0, size, y0 + strip_h], fill=STRIP)
    label = "v" + version
    font = ImageFont.load_default(size=max(10, int(strip_h * 0.72)))
    bbox = d.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2, y0 + (strip_h - th) / 2 - bbox[1]), label, font=font, fill=TEXT)
    return img


def main():
    version = sys.argv[1]
    res = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "android", "app", "src", "main", "res")
    for dens, size in DENSITIES.items():
        out_dir = os.path.abspath(os.path.join(res, "mipmap-" + dens))
        os.makedirs(out_dir, exist_ok=True)
        render(size, version).save(os.path.join(out_dir, "ic_launcher.png"))


if __name__ == "__main__":
    main()
