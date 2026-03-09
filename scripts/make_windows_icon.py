#!/usr/bin/env python3
"""Convert the shared PNG app icon into a Windows .ico file."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def main() -> int:
    scripts_dir = Path(__file__).resolve().parent
    src = scripts_dir / "coco.png"
    dst = scripts_dir / "coco.ico"

    with Image.open(src) as image:
        image.save(dst, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

    print(f"Wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
