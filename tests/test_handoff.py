"""Offline unit checks; run: python -m unittest discover -s tests -v."""
from pathlib import Path
import importlib.util
import re
import subprocess
import sys
import unittest

from _tempdir_helper import test_tempdir

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
            # Retargeted to the native XR30 eMMC target.
            self.assertIn(f'CONFIG_TARGET_mediatek_mt7981_DEVICE_{c.TARGET_DEVICE}=y', result)
            self.assertNotIn(f'CONFIG_TARGET_mediatek_mt7981_DEVICE_{c.LEGACY_DEVICE}=y', result)
        self.assertNotIn('CONFIG_PACKAGE_luci-app-openclash=y', c.make_config(base, 'baseline'))
        self.assertIn('CONFIG_PACKAGE_luci-app-openclash=y', c.make_config(base, 'performance'))

    def test_baseline_drops_author_proxy_and_docker_leftovers(self):
        c = load_configure()
        base = (ROOT / 'configs/rax3000z-emmc.config').read_text()
        result = c.make_config(base, 'baseline')
        c.verify_config(result, 'baseline')
        for pkg in ('docker', 'dockerd', 'v2raya', 'xray-core', 'zerotier',
                    'luci-app-docker'):
            self.assertIn(f'# CONFIG_PACKAGE_{pkg} is not set', result)
        for pkg in ('kmod-ipt-nat', 'kmod-ifb'):
            self.assertIn(f'CONFIG_PACKAGE_{pkg}=y', result)

    def test_author_led_source_when_merged(self):
        path = ROOT / 'mt7981-cmcc-xr30-emmc.dtsi'
        if not path.exists():
            self.skipTest('Original author DTSI expected only after merging into Fork')
        self.assertIn('gpios = <&pio 34 GPIO_ACTIVE_LOW>;', path.read_text())

    def test_new_layout_led_patch_keeps_shared_include(self):
        content = """/dts-v1/;\n#include "mt7981-cmcc-rax3000m-xr30.dtsi"\n/ {\n\taliases {\n\t\tled-running = &green_led;\n\t\tled-upgrade = &blue_led;\n\t};\n\tleds {\n\t\tgreen_led: green {\n\t\t\tlabel = "rax3000m:green";\n\t\t\tgpios = <&pio 9 GPIO_ACTIVE_LOW>;\n\t\t};\n\n\t\tblue_led: blue {\n\t\t\tlabel = "rax3000m:blue";\n\t\t\tgpios = <&pio 12 GPIO_ACTIVE_LOW>;\n\t\t};\n\t};\n};\n"""
        with test_tempdir() as temp:
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
        with test_tempdir() as temp:
            fixture=Path(temp)/'legacy.dtsi';fixture.write_text('white_led: white { gpios = <&pio 34 GPIO_ACTIVE_LOW>; };\n')
            p=Path(temp)/'input.dtsi';p.write_text('#include "unknown-board.dtsi"\n')
            r=subprocess.run([sys.executable,str(ROOT/'scripts/patch_led.py'),str(p),str(fixture)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('unknown DTSI layout',r.stderr + r.stdout)

    def test_irqbalance_and_ops_packages_follow_profile_tiers(self):
        c = load_configure()
        base = (ROOT / 'configs/rax3000z-emmc.config').read_text()
        baseline = c.make_config(base, 'baseline')
        perf = c.make_config(base, 'performance')
        full = c.make_config(base, 'full')
        # irqbalance rides with performance/full, never baseline.
        self.assertIn('CONFIG_PACKAGE_irqbalance=y', perf)
        self.assertIn('CONFIG_PACKAGE_irqbalance=y', full)
        self.assertNotIn('CONFIG_PACKAGE_irqbalance=y', baseline)
        # Tailscale/AdGuard LuCI and the ops tools are full-only.
        for pkg in ('luci-app-tailscale-lite', 'luci-app-adguardhome',
                    'luci-app-statistics', 'luci-app-vnstat2',
                    'luci-app-watchcat', 'luci-app-wol'):
            self.assertIn(f'CONFIG_PACKAGE_{pkg}=y', full,
                          f'{pkg} must be selected in full')
            self.assertNotIn(f'CONFIG_PACKAGE_{pkg}=y', perf,
                             f'{pkg} must not leak into performance')
        # Tuning rides with performance/full, never baseline.
        self.assertIn('CONFIG_PACKAGE_xr30-network-tuning=y', perf)
        self.assertIn('CONFIG_PACKAGE_xr30-network-tuning=y', full)
        self.assertNotIn('CONFIG_PACKAGE_xr30-network-tuning=y', baseline)

    def test_tuning_package_governor_script(self):
        initd = (ROOT / 'packages/xr30-network-tuning/files/etc/init.d/xr30-cpufreq')
        enabler = (ROOT / 'packages/xr30-network-tuning/files/etc/uci-defaults/98-xr30-cpufreq-enable')
        self.assertTrue(initd.is_file())
        self.assertTrue(enabler.is_file())
        text = initd.read_text()
        # schedutil is the conservative choice; performance would pin both
        # cores at max frequency and raise thermals for no benefit at idle.
        self.assertIn('GOVERNOR="schedutil"', text)
        self.assertIn('scaling_available_governors', text,
                      'must verify the governor is available before writing')
        self.assertIn('scaling_governor', text)
        self.assertIn('START=', text, 'must be an rc.common boot script')
        # The governor must be applied at every boot, so a bare uci-defaults
        # one-shot is not enough; the uci-defaults file only enables the init.
        self.assertIn('/etc/init.d/xr30-cpufreq enable', enabler.read_text())

    def test_retarget_drops_legacy_device_and_sets_profile(self):
        c = load_configure()
        base = (ROOT / 'configs/rax3000z-emmc.config').read_text()
        result = c.make_config(base, 'full')
        self.assertIn(f'CONFIG_TARGET_mediatek_mt7981_DEVICE_{c.TARGET_DEVICE}=y', result)
        self.assertIn(f'CONFIG_TARGET_PROFILE="DEVICE_{c.TARGET_DEVICE}"', result)
        # The legacy selection must be gone, both the device flag and the
        # PROFILE string, or make defconfig would pick the wrong board.
        self.assertNotIn(f'DEVICE_{c.LEGACY_DEVICE}=y', result)
        self.assertNotIn(f'CONFIG_TARGET_PROFILE="DEVICE_{c.LEGACY_DEVICE}"', result)
        self.assertEqual(result.count('CONFIG_TARGET_PROFILE='), 1,
                         'exactly one target profile line expected')

    def test_in_tree_tailscale_page_is_lua_only(self):
        d = ROOT / 'packages/luci-app-tailscale-lite'
        self.assertTrue((d / 'Makefile').is_file())
        self.assertTrue((d / 'luasrc/controller/tailscale.lua').is_file())
        self.assertTrue((d / 'luasrc/model/cbi/tailscale/status.lua').is_file())
        # Upstream luci-app-tailscale ships JS views that the 21.02 Lua LuCI
        # cannot render; any .js here would regress to a blank page.
        self.assertEqual([p.name for p in d.rglob('*.js')], [],
                         'luci-app-tailscale-lite must stay Lua-only')
        model = (d / 'luasrc/model/cbi/tailscale/status.lua').read_text()
        self.assertIn('require "luci.jsonc"', model)
        self.assertIn('require "nixio.fs"', model)
        controller = (d / 'luasrc/controller/tailscale.lua').read_text()
        self.assertIn('"admin", "services", "tailscale"', controller)
        self.assertIn('nixio.fs.access("/usr/sbin/tailscale")', controller,
                      'controller must fail closed when tailscale is absent')

    def test_third_party_source_is_pinned_not_a_branch_head(self):
        text = (ROOT / 'scripts/custom_prepare.sh').read_text()
        self.assertIsNotNone(re.search(r"KENZOK8_SHA='[0-9a-f]{40}'", text),
                             'kenzok8 feed must be pinned by full SHA')
        self.assertIn('codeload.github.com', text,
                      'pinned sources should be fetched as a commit tarball')
        # The AGH LuCI must reuse our compiled binary, not bundle a second one.
        self.assertIn('INCLUDE_binary', text)

    def test_workflow_verifies_lua_compatibility(self):
        y = (ROOT / '.github/workflows/build-xr30-custom.yml').read_text()
        self.assertIn('Verify third-party and in-tree package sources', y)
        self.assertIn('luci-app-tailscale-lite must stay Lua-only', y)
        self.assertIn('luci-app-adguardhome menu became JS-view', y)
        self.assertIn('kenzok8-source-sha.txt', y)

if __name__ == '__main__':
    unittest.main()
