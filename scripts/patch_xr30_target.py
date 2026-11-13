#!/usr/bin/env python3
"""Retarget the build to the native XR30 eMMC DTS and pin eMMC to 26 MHz.

Upstream added a native cmcc_xr30-emmc target whose DTSI already carries the
XR30 white LED on GPIO34, so no LED patch is needed. Its stock DTS however runs
the eMMC at 52 MHz; the author's README warns that on marginal flash this can
cause I/O errors, unusable firmware or a device that will not boot. This unit
has always run at 26 MHz, so we pin it back and refuse anything unexpected.

This tool only edits files inside the build tree. It never touches the router.
"""
import re
import sys
from pathlib import Path

TARGET_HZ = "26000000"
UNSAFE_HZ = "52000000"


def patch_leds(dtsi):
    """Require the white LED to be native; we do not inject it here."""
    text = dtsi.read_text()
    problems = []
    if "white_led" not in text:
        problems.append("no white_led node")
    if "gpios = <&pio 34 GPIO_ACTIVE_LOW>;" not in text:
        problems.append("white LED is not on GPIO34")
    if "led-running = &white_led;" not in text:
        problems.append("led-running does not reference white_led")
    if "&green_led" in text or "&blue_led" in text:
        problems.append("still references green/blue LEDs")
    if problems:
        sys.exit(
            "ERROR: native XR30 DTSI no longer matches expectations ("
            + "; ".join(problems)
            + "); manual audit required before building")
    return text


def patch_emmc(dts):
    """Force exactly one max-frequency from 52 MHz to 26 MHz."""
    text = dts.read_text()
    pattern = re.compile(r"max-frequency\s*=\s*<\s*" + UNSAFE_HZ + r"\s*>\s*;")
    found = pattern.findall(text)
    if len(found) != 1:
        # Either upstream changed the clock, or there are several nodes.
        all_hits = re.findall(r"max-frequency\s*=\s*<(\d+)>\s*;", text)
        sys.exit(
            f"ERROR: expected exactly one max-frequency = <{UNSAFE_HZ}>, "
            f"found values {all_hits}; refusing to guess")
    patched = pattern.sub(f"max-frequency = <{TARGET_HZ}>;", text)
    if f"max-frequency = <{TARGET_HZ}>;" not in patched:
        sys.exit("ERROR: eMMC frequency substitution did not apply")
    if UNSAFE_HZ in patched:
        sys.exit("ERROR: 52 MHz still present after patch")
    if patched.count("max-frequency") != 1:
        sys.exit("ERROR: unexpected number of max-frequency properties after patch")
    return patched


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: patch_xr30_target.py <mt7981-cmcc-xr30-emmc.dts> <mt7981-cmcc-xr30.dtsi>")

    dts = Path(sys.argv[1])
    dtsi = Path(sys.argv[2])
    for path in (dts, dtsi):
        if not path.is_file():
            sys.exit(f"ERROR: missing upstream file: {path}")

    patch_leds(dtsi)

    if "mt7981-cmcc-xr30.dtsi" not in dts.read_text():
        sys.exit("ERROR: eMMC DTS no longer includes mt7981-cmcc-xr30.dtsi; layout drifted")

    dts.write_text(patch_emmc(dts))
    print(f"OK: native XR30 LEDs kept, eMMC pinned to 26 MHz (was {UNSAFE_HZ})")


if __name__ == "__main__":
    main()
