"""Offline unit checks; run: python -m unittest discover -s tests -v."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]

def load_configure():
    spec = importlib.util.spec_from_file_location('xr30_configure', ROOT / 'scripts/configure.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class OverlayUnitTests(unittest.TestCase):
    def test_profiles_add_and_remove_required_packages(self):
        c = load_configure()
        base_path = ROOT / 'configs/rax3000z-emmc.config'
        base = (base_path.read_text() if base_path.exists() else
                'CONFIG_TARGET_mediatek_mt7981_DEVICE_cmcc_rax3000m-emmc=y\n'
                'CONFIG_PACKAGE_luci-app-v2raya=y\n')
        for profile in ('baseline', 'performance', 'full'):
            result = c.make_config(base, profile)
            c.verify_config(result, profile)
            self.assertIn('CONFIG_TARGET_mediatek_mt7981_DEVICE_cmcc_rax3000m-emmc=y', result)
        self.assertNotIn('CONFIG_PACKAGE_luci-app-openclash=y', c.make_config(base, 'baseline'))
        self.assertIn('CONFIG_PACKAGE_luci-app-openclash=y', c.make_config(base, 'performance'))

    def test_author_led_source_when_merged(self):
        path = ROOT / 'mt7981-cmcc-xr30-emmc.dtsi'
        if not path.exists():
            self.skipTest('Original author DTSI expected only after merging into Fork')
        self.assertIn('gpios = <&pio 34 GPIO_ACTIVE_LOW>;', path.read_text())

    def test_new_layout_led_patch_keeps_shared_include(self):
        content = """/dts-v1/;\n#include "mt7981-cmcc-rax3000m-xr30.dtsi"\n/ {\n\taliases {\n\t\tled-running = &green_led;\n\t\tled-upgrade = &blue_led;\n\t};\n\tleds {\n\t\tgreen_led: green {\n\t\t\tlabel = "rax3000m:green";\n\t\t\tgpios = <&pio 9 GPIO_ACTIVE_LOW>;\n\t\t};\n\n\t\tblue_led: blue {\n\t\t\tlabel = "rax3000m:blue";\n\t\t\tgpios = <&pio 12 GPIO_ACTIVE_LOW>;\n\t\t};\n\t};\n};\n"""
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / 'legacy.dtsi'
            fixture.write_text('/dts-v1/;\nwhite_led: white {\n  gpios = <&pio 34 GPIO_ACTIVE_LOW>;\n};\n')
            p = Path(temp) / 'input.dtsi'
            p.write_text(content)
            cmd = [sys.executable, str(ROOT / 'scripts/patch_led.py'), str(p), str(fixture)]
            out = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            patched=p.read_text()
            self.assertIn('#include "mt7981-cmcc-rax3000m-xr30.dtsi"', patched)
            self.assertIn('gpios = <&pio 34 GPIO_ACTIVE_LOW>;', patched)
            self.assertNotIn('green_led', patched)
            self.assertNotIn('blue_led', patched)

    def test_source_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            fixture=Path(temp)/'legacy.dtsi';fixture.write_text('white_led: white { gpios = <&pio 34 GPIO_ACTIVE_LOW>; };\n')
            p=Path(temp)/'input.dtsi';p.write_text('#include "unknown-board.dtsi"\n')
            r=subprocess.run([sys.executable,str(ROOT/'scripts/patch_led.py'),str(p),str(fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('unknown DTSI layout',r.stderr + r.stdout)

if __name__ == '__main__':
    unittest.main()
