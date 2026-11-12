#!/usr/bin/env python3
"""Inventory build artifacts and enforce the XR30 eMMC partition limits.

This is NOT a flashing compatibility test. It only proves that each generated
sysupgrade archive fits the verified GPT layout: p4 kernel 32 MiB and p5
rootfs 2 GiB. Firmware metadata, U-Boot compatibility and the router itself
must still be checked separately.
"""
import hashlib
import pathlib
import sys
import tarfile

KERNEL_LIMIT = 32 * 1024 * 1024
ROOT_LIMIT = 2 * 1024 * 1024 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tar_sizes(image):
    """Return (kernel_bytes, root_bytes) from an OpenWrt sysupgrade tar."""
    try:
        with tarfile.open(image, mode="r:") as tar:
            files = [member for member in tar.getmembers() if member.isfile()]
    except (tarfile.TarError, OSError) as exc:
        raise ValueError(f"not a readable sysupgrade tar: {exc}") from exc
    picked = {}
    for wanted in ("kernel", "root"):
        hits = [
            member for member in files
            if member.name.startswith("sysupgrade-")
            and member.name.endswith("/" + wanted)
        ]
        if len(hits) != 1:
            raise ValueError(
                f"expected one sysupgrade-*/{wanted} entry, found {len(hits)}")
        picked[wanted] = hits[0]
    kernel_dir = picked["kernel"].name.rsplit("/", 1)[0]
    root_dir = picked["root"].name.rsplit("/", 1)[0]
    if kernel_dir != root_dir:
        raise ValueError("kernel and root come from different sysupgrade directories")
    return picked["kernel"].size, picked["root"].size


def limit_errors(kernel, root):
    errors = []
    if kernel > KERNEL_LIMIT:
        errors.append(f"kernel {kernel:,} bytes exceeds p4 limit {KERNEL_LIMIT:,} bytes")
    if root > ROOT_LIMIT:
        errors.append(f"root {root:,} bytes exceeds p5 limit {ROOT_LIMIT:,} bytes")
    return errors


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not root.is_dir():
        sys.exit(f"ERROR: target folder missing: {root}")
    images = sorted(root.glob("*sysupgrade*.bin"))
    if not images:
        sys.exit("ERROR: no sysupgrade image was generated")

    failures = []
    lines = [
        "Build artifacts only; NOT certified flashable on XR30 eMMC.",
        f"Limits: kernel <= {KERNEL_LIMIT:,} bytes (p4 32 MiB), "
        f"rootfs <= {ROOT_LIMIT:,} bytes (p5 2 GiB).",
    ]
    for path in images:
        digest = sha256(path)
        lines.append(f"{digest}  {path}  ({path.stat().st_size} bytes)")
        try:
            kernel, rootfs = tar_sizes(path)
        except ValueError as exc:
            failures.append(f"{path.name}: {exc}")
            lines.append(f"  UNVERIFIED: {exc}")
            continue
        lines.append(f"  kernel={kernel:,} bytes  root={rootfs:,} bytes")
        for error in limit_errors(kernel, rootfs):
            failures.append(f"{path.name}: {error}")

    text = "\n".join(lines) + "\n"
    if failures:
        text += "RESULT: FAIL\n" + "".join(f"FAIL: {item}\n" for item in failures)
    else:
        text += "RESULT: PASS\n"
    pathlib.Path("image-inventory.txt").write_text(text, encoding="utf-8")
    print(text)
    if failures:
        for item in failures:
            print("FAIL:", item, file=sys.stderr)
        return 1
    print("PASS: image inventory recorded and partition limits satisfied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
