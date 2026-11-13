"""patch_led.py must handle the real upstream DTS layouts.

Two layouts exist in hanwckf/immortalwrt-mt798x:
  - old inline layout (what we pinned at ab766cb, 2024-06): the board DTSI
    defines ethernet, switch, HNAT and LEDs itself.
  - new refactored layout (740103d, 2026-09 onward): the board DTSI includes
    mt7981-cmcc-rax3000m-xr30.dtsi and only keeps LEDs.

Both must receive the XR30 white LED on GPIO34, and anything else must fail
closed. The fixtures below are the verbatim content of those files so a drift
in upstream structure is caught here rather than on the router.
"""
import pathlib
import subprocess
import sys
import unittest

from _tempdir_helper import test_tempdir

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Verbatim: mt7981-cmcc-rax3000m.dtsi at 740103d (2026-09-11).
NEW_LAYOUT_DTSI = """/dts-v1/;
#include "mt7981-cmcc-rax3000m-xr30.dtsi"

/ {
\taliases {
\t\tled-boot = &red_led;
\t\tled-failsafe = &red_led;
\t\tled-running = &green_led;
\t\tled-upgrade = &blue_led;
\t};

\tleds {
\t\tcompatible = "gpio-leds";

\t\tred_led: red {
\t\t\tlabel = "rax3000m:red";
\t\t\tgpios = <&pio 35 GPIO_ACTIVE_LOW>;
\t\t};

\t\tgreen_led: green {
\t\t\tlabel = "rax3000m:green";
\t\t\tgpios = <&pio 9 GPIO_ACTIVE_LOW>;
\t\t};

\t\tblue_led: blue {
\t\t\tlabel = "rax3000m:blue";
\t\t\tgpios = <&pio 12 GPIO_ACTIVE_LOW>;
\t\t};
\t};
};
"""

# Shape of mt7981-cmcc-rax3000m.dtsi at ab766cb (2024-06): inline hardware.
OLD_LAYOUT_DTSI = """/dts-v1/;
#include "mt7981.dtsi"

/ {
\taliases {
\t\tled-running = &green_led;
\t\tled-upgrade = &blue_led;
\t};

\tleds {
\t\tcompatible = "gpio-leds";

\t\tgreen_led: green {
\t\t\tlabel = "rax3000m:green";
\t\t\tgpios = <&pio 9 GPIO_ACTIVE_LOW>;
\t\t};

\t\tblue_led: blue {
\t\t\tlabel = "rax3000m:blue";
\t\t\tgpios = <&pio 12 GPIO_ACTIVE_LOW>;
\t\t};
\t};
};
"""


def run_patch(tmp, content):
    target = pathlib.Path(tmp) / 'mt7981-cmcc-rax3000m.dtsi'
    target.write_text(content)
    legacy = ROOT / 'mt7981-cmcc-xr30-emmc.dtsi'
    proc = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/patch_led.py'), str(target), str(legacy)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc, target


class UpstreamDtsLayoutTests(unittest.TestCase):
    def test_new_refactored_layout_gets_white_led(self):
        with test_tempdir() as tmp:
            proc, target = run_patch(tmp, NEW_LAYOUT_DTSI)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            patched = target.read_text()
            # Shared hardware include must survive: only LEDs may change.
            self.assertIn('#include "mt7981-cmcc-rax3000m-xr30.dtsi"', patched)
            self.assertIn('gpios = <&pio 34 GPIO_ACTIVE_LOW>;', patched)
            self.assertIn('led-running = &white_led;', patched)
            self.assertIn('led-upgrade = &white_led;', patched)
            self.assertNotIn('green_led', patched)
            self.assertNotIn('blue_led', patched)
            # Red boot/failsafe LED is deliberately left alone.
            self.assertIn('led-boot = &red_led;', patched)
            self.assertIn('led-failsafe = &red_led;', patched)

    def test_old_inline_layout_uses_author_dtsi(self):
        with test_tempdir() as tmp:
            proc, target = run_patch(tmp, OLD_LAYOUT_DTSI)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            patched = target.read_text()
            self.assertIn('gpios = <&pio 34 GPIO_ACTIVE_LOW>;', patched)
            self.assertIn('white_led', patched)

    def test_unknown_layout_is_rejected(self):
        with test_tempdir() as tmp:
            proc, _ = run_patch(tmp, '/dts-v1/;\n#include "some-other-board.dtsi"\n')
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('unknown DTSI layout', proc.stdout + proc.stderr)

    def test_drifted_led_block_is_rejected(self):
        # Same include but different LED definitions: must not silently patch.
        drifted = NEW_LAYOUT_DTSI.replace('gpios = <&pio 9 GPIO_ACTIVE_LOW>;',
                                          'gpios = <&pio 7 GPIO_ACTIVE_LOW>;')
        with test_tempdir() as tmp:
            proc, _ = run_patch(tmp, drifted)
            self.assertNotEqual(proc.returncode, 0)
            combined = proc.stdout + proc.stderr
            self.assertIn('drifted', combined.lower())


if __name__ == '__main__':
    unittest.main()
