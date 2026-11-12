#!/usr/bin/env python3
"""Apply XR30 white LED adaptation without replacing new upstream hardware code.

For new hanwckf DTSI layout, patch ONLY LED names/GPIO and aliases.
For old layout, reuse Star-Song's complete verified legacy DTSI.
Fail on unknown layout; never silently flash mismatched DTS.
"""
from pathlib import Path
import sys

if len(sys.argv) != 3:
    sys.exit("Usage: patch_led.py upstream-mt7981-cmcc-rax3000m.dtsi original-xr30.dtsi")
base, legacy = [Path(s) for s in sys.argv[1:]]
if not base.is_file() or not legacy.is_file():
    sys.exit("ERROR: missing upstream DTSI or Star-Song XR30 DTSI")
src = base.read_text()
if '#include "mt7981-cmcc-rax3000m-xr30.dtsi"' in src:
    # New hanwckf refactoring has shared switch, ethernet and HNAT definitions
    # in mt7981-cmcc-rax3000m-xr30.dtsi: keep them intact.
    before = """\t\tgreen_led: green {
\t\t\tlabel = \"rax3000m:green\";
\t\t\tgpios = <&pio 9 GPIO_ACTIVE_LOW>;
\t\t};

\t\tblue_led: blue {
\t\t\tlabel = \"rax3000m:blue\";
\t\t\tgpios = <&pio 12 GPIO_ACTIVE_LOW>;
\t\t};"""
    after = """\t\twhite_led: white {
\t\t\tlabel = \"rax3000z:white\";
\t\t\tgpios = <&pio 34 GPIO_ACTIVE_LOW>;
\t\t};"""
    substitutions = {
        "led-running = &green_led;": "led-running = &white_led;",
        "led-upgrade = &blue_led;": "led-upgrade = &white_led;",
        before: after,
    }
    for old, new in substitutions.items():
        if src.count(old) != 1:
            sys.exit("ERROR: upstream LED layout drifted; refusing an unsafe automatic DTSI patch: " + old[:50])
        src = src.replace(old, new, 1)
    if '&green_led' in src or '&blue_led' in src:
        sys.exit("ERROR: unresolved old LED labels")
    base.write_text(src)
    print("OK: applied minimal XR30 LED-only patch to new refactored DTSI")
elif '#include "mt7981.dtsi"' in src:
    # The 2024 build replaced the entire DTSI because hardware was inline.
    patch = legacy.read_text()
    if 'gpios = <&pio 34 GPIO_ACTIVE_LOW>;' not in patch or 'white_led' not in patch:
        sys.exit("ERROR: supplied XR30 legacy DTSI lacks GPIO34 white LED")
    base.write_text(patch)
    print("OK: applied original Star-Song full DTSI to old inline layout")
else:
    sys.exit("ERROR: unknown DTSI layout, manual audit required")
