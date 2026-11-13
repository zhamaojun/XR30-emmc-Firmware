"""patch_xr30_target.py must pin the native XR30 DTS to 26 MHz, safely.

Fixtures are the verbatim upstream files at 740103d so structural drift is
caught here instead of on the router.
"""
import pathlib
import subprocess
import sys
import unittest

from _tempdir_helper import test_tempdir

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Verbatim: mt7981-cmcc-xr30.dtsi at 740103d - white LED already native.
GOOD_DTSI = """/dts-v1/;
#include "mt7981-cmcc-rax3000m-xr30.dtsi"

/ {
\taliases {
\t\tled-boot = &red_led;
\t\tled-failsafe = &red_led;
\t\tled-running = &white_led;
\t\tled-upgrade = &red_led;
\t};

\tleds {
\t\tcompatible = "gpio-leds";

\t\tred_led: red {
\t\t\tlabel = "xr30:red";
\t\t\tgpios = <&pio 35 GPIO_ACTIVE_LOW>;
\t\t};

\t\twhite_led: white {
\t\t\tlabel = "xr30:white";
\t\t\tgpios = <&pio 34 GPIO_ACTIVE_LOW>;
\t\t};
\t};
};
"""

# Verbatim: mt7981-cmcc-xr30-emmc.dts at 740103d - eMMC at 52 MHz.
GOOD_DTS = """/dts-v1/;
#include "mt7981-cmcc-xr30.dtsi"

/ {
\tmodel = "CMCC XR30 eMMC version (RAX3000Z Enhanced version)";
\tcompatible = "cmcc,xr30-emmc", "mediatek,mt7981";
};

&mmc0 {
\tbus-width = <8>;
\tcap-mmc-highspeed;
\tmax-frequency = <52000000>;
\tno-sd;
\tno-sdio;
\tnon-removable;
\tstatus = "okay";
};
"""


def run_patch(tmp, dts_text, dtsi_text):
    base = pathlib.Path(tmp)
    dts = base / 'mt7981-cmcc-xr30-emmc.dts'
    dtsi = base / 'mt7981-cmcc-xr30.dtsi'
    dts.write_text(dts_text)
    dtsi.write_text(dtsi_text)
    proc = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/patch_xr30_target.py'), str(dts), str(dtsi)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc, dts


class PatchXr30TargetTests(unittest.TestCase):
    def test_pins_emmc_to_26mhz_and_keeps_native_white_led(self):
        with test_tempdir() as tmp:
            proc, dts = run_patch(tmp, GOOD_DTS, GOOD_DTSI)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            patched = dts.read_text()
            self.assertIn('max-frequency = <26000000>;', patched)
            self.assertNotIn('52000000', patched)
            self.assertIn('#include "mt7981-cmcc-xr30.dtsi"', patched)
            # Hardware flags unrelated to the clock must survive.
            self.assertIn('bus-width = <8>;', patched)
            self.assertIn('non-removable;', patched)

    def test_refuses_when_white_led_moved_off_gpio34(self):
        bad = GOOD_DTSI.replace('gpios = <&pio 34 GPIO_ACTIVE_LOW>;',
                                'gpios = <&pio 33 GPIO_ACTIVE_LOW>;')
        with test_tempdir() as tmp:
            proc, _ = run_patch(tmp, GOOD_DTS, bad)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('GPIO34', proc.stdout + proc.stderr)

    def test_refuses_when_clock_already_changed(self):
        # If upstream moves to a different clock we must not silently patch.
        already = GOOD_DTS.replace('52000000', '40000000')
        with test_tempdir() as tmp:
            proc, _ = run_patch(tmp, already, GOOD_DTSI)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('max-frequency', proc.stdout + proc.stderr)

    def test_refuses_on_multiple_clock_nodes(self):
        doubled = GOOD_DTS.replace(
            '&mmc0 {',
            '&mmc1 {\n\tmax-frequency = <52000000>;\n};\n\n&mmc0 {')
        with test_tempdir() as tmp:
            proc, _ = run_patch(tmp, doubled, GOOD_DTSI)
            self.assertNotEqual(proc.returncode, 0)

    def test_refuses_when_dts_does_not_include_xr30_dtsi(self):
        bad = GOOD_DTS.replace('#include "mt7981-cmcc-xr30.dtsi"',
                               '#include "something-else.dtsi"')
        with test_tempdir() as tmp:
            proc, _ = run_patch(tmp, bad, GOOD_DTSI)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('layout drifted', proc.stdout + proc.stderr)


if __name__ == '__main__':
    unittest.main()
