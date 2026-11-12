#!/usr/bin/env python3
"""Image inventory is not a flashing compatibility test."""
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
if not root.is_dir():
    sys.exit(f"ERROR: target folder missing: {root}")
images = sorted(root.glob("*sysupgrade*.bin"))
if not images:
    sys.exit("ERROR: no sysupgrade image was generated")
with open("image-inventory.txt", "w") as fp:
    fp.write("Build artifacts only; NOT certified flashable on XR30 eMMC.\n")
    for path in images:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        fp.write(f"{digest.hexdigest()}  {path}  ({path.stat().st_size} bytes)\n")
print(pathlib.Path("image-inventory.txt").read_text())
