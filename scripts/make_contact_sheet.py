"""Render a contact sheet from confirmed, readable keyframe files."""
import argparse
import json
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--columns", type=int, default=4)
    args = parser.parse_args()
    entries = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    if not entries or args.columns < 1:
        parser.error("Need at least one frame and positive columns")
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"KF_\d{3,}", x) for x in ids):
        parser.error("Expected unique KF_001-style IDs")
    if any(entry.get("status") != "passed" for entry in entries):
        parser.error("All frames must be confirmed with status passed")
    for entry in entries:
        if not entry.get("path"):
            parser.error("Each frame requires a file path")
        path = args.manifest.parent / entry["path"]
        if not path.is_file():
            parser.error(f"Missing frame file: {path}")
    if args.output.exists():
        parser.error("Output exists; choose a new version path")
    entries.sort(key=lambda x: int(x["id"].split("_")[1]))
    width, height, label, gap = 384, 216, 32, 12
    cols = min(args.columns, len(entries))
    rows = math.ceil(len(entries) / cols)
    sheet = Image.new("RGB", (cols * (width + gap) + gap,
                               rows * (height + label + gap) + gap), "#15191f")
    draw = ImageDraw.Draw(sheet)
    for index, entry in enumerate(entries):
        x = gap + index % cols * (width + gap)
        y = gap + index // cols * (height + label + gap)
        path = args.manifest.parent / entry["path"]
        with Image.open(path) as source:
            thumb = ImageOps.contain(ImageOps.exif_transpose(source).convert("RGB"), (width, height))
            sheet.paste(thumb, (x + (width - thumb.width) // 2, y + (height - thumb.height) // 2))
        draw.text((x + 4, y + height + 8), entry["id"] + " | passed", fill="#9be6b0")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as output:
        sheet.save(output, format="PNG")
    print(json.dumps({"output": str(args.output.resolve()), "frames": len(entries),
                      "missing": 0, "not_passed": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
