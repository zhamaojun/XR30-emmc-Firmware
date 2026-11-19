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
        # irqbalance was measured ineffective on this board (20s after start
        # the per-CPU counters were unchanged) and is removed everywhere.
        for name, cfg in (('baseline', baseline), ('performance', perf), ('full', full)):
            self.assertNotIn('CONFIG_PACKAGE_irqbalance=y', cfg,
                             f'irqbalance must not be selected in {name}')
        # Docker removed: br_netfilter forces bridged traffic through
        # iptables and conflicts with the CAKE data path.
        for pkg in ('docker', 'dockerd', 'luci-app-dockerman', 'luci-lib-docker'):
            for name, cfg in (('baseline', baseline), ('performance', perf), ('full', full)):
                self.assertNotIn(f'CONFIG_PACKAGE_{pkg}=y', cfg,
                                 f'{pkg} must not be selected in {name}')
        # Tailscale/AdGuard LuCI and the ops tools are full-only.
        for pkg in ('luci-app-tailscale-lite', 'luci-app-adguardhome',
                    'luci-app-statistics', 'luci-app-vnstat2',
                    'luci-app-watchcat', 'luci-app-wol'):
            self.assertIn(f'CONFIG_PACKAGE_{pkg}=y', full,
                          f'{pkg} must be selected in full')
            self.assertNotIn(f'CONFIG_PACKAGE_{pkg}=y', perf,
                             f'{pkg} must not leak into performance')
        # Tuning and SQM ride with performance/full, never baseline.
        for pkg in ('xr30-network-tuning', 'luci-app-sqm', 'sqm-scripts',
                    'kmod-sched-cake'):
            self.assertIn(f'CONFIG_PACKAGE_{pkg}=y', perf, f'{pkg} in performance')
            self.assertIn(f'CONFIG_PACKAGE_{pkg}=y', full, f'{pkg} in full')
            self.assertNotIn(f'CONFIG_PACKAGE_{pkg}=y', baseline, f'{pkg} not in baseline')

    def test_game_latency_defaults_are_cake_with_hant_off(self):
        script = (ROOT / 'packages/xr30-network-tuning/files/etc/uci-defaults/'
                          '97-xr30-game-latency')
        self.assertTrue(script.is_file())
        text = script.read_text()
        # CAKE shapes both directions with per-host fairness behind NAT.
        self.assertIn("set sqm.wan.qdisc='cake'", text)
        self.assertIn("set sqm.wan.script='piece_of_cake.qos'", text)
        self.assertIn('nat dual-dsthost', text)
        self.assertIn('nat dual-srchost', text)
        # Values must stay below the measured 120/80 Mbit line, otherwise the
        # bottleneck queue stays full and shaping does nothing.
        self.assertIn("set sqm.wan.download='110400'", text)
        self.assertIn("set sqm.wan.upload='73600'", text)
        # HNAT bypasses the qdisc, so it has to be off for CAKE to work.
        # 'disabled' is the valid TurboACC ListValue; 'none' is not an option.
        self.assertIn("set turboacc.config.fastpath='disabled'", text)
        self.assertNotIn("fastpath='none'", text,
                         "TurboACC has no 'none' option; use 'disabled'")
        # TurboACC rewrites congestion control at boot; BBR must be pinned
        # there too or the sysctl setting is lost on every restart.
        self.assertIn("set turboacc.config.tcpcca='bbr'", text)
        # Baseline has no SQM package; the script must no-op there.
        self.assertIn('/etc/init.d/sqm ] || exit 0', text)

    def test_game_latency_claims_turboacc_guard_before_its_own_defaults(self):
        """Regression: luci-app-turboacc-mtk ships uci-defaults/turboacc.

        That script REPLACES /etc/config/turboacc wholesale and then selects
        fastpath=mediatek_hnat when mtkhnat.ko exists. Letters sort after
        digits, so it ran after "97-" and wiped HNAT-off + BBR on the first
        boot of the 2026-11-20 build. It exits early on turboacc.global.set=1,
        so that flag must be claimed first.
        """
        text = (ROOT / 'packages/xr30-network-tuning/files/etc/uci-defaults/'
                        '97-xr30-game-latency').read_text()
        guard = "set turboacc.global.set='1'"
        self.assertIn(guard, text)
        # The guard only helps if it precedes every other turboacc write:
        # the clobbering script bails out before we would write our values.
        self.assertLess(text.index(guard),
                        text.index("set turboacc.config.fastpath='disabled'"),
                        'global.set must be claimed before fastpath')
        self.assertLess(text.index(guard),
                        text.index("set turboacc.config.tcpcca='bbr'"),
                        'global.set must be claimed before tcpcca')
        # TurboACC has to be configured even when SQM is absent (baseline), so
        # the block cannot sit behind the sqm guard.
        self.assertLess(text.index("set turboacc.config.fastpath='disabled'"),
                        text.index('/etc/init.d/sqm ] || exit 0'),
                        'turboacc config must not be gated on SQM')
        # Taking the early exit skips turboacc's own ucitrack registration.
        self.assertIn("set ucitrack.@turboacc[-1].init=turboacc", text)
        # Drop an already-raised HNAT hook now: rc.d links created during this
        # boot only take effect from the next one.
        self.assertIn('/sys/kernel/debug/hnat/hook_toggle', text)

    def test_game_latency_detects_pppoe_wan(self):
        """PPPoE needs a different netdev and a non-zero overhead.

        Following network.wan.device on a PPPoE line points at the raw
        ethernet port, so the shaper sits on a device the traffic never
        leaves through; and overhead=0 makes CAKE underestimate the wire
        rate, leaving the standing queue SQM is supposed to remove.
        """
        text = (ROOT / 'packages/xr30-network-tuning/files/etc/uci-defaults/'
                        '97-xr30-game-latency').read_text()
        self.assertIn('pppoe)', text)
        self.assertIn('WAN_DEV="pppoe-wan"', text)
        self.assertIn('OVERHEAD=8', text)
        # overhead must be written from the detected value, not hard-coded.
        self.assertIn("set sqm.wan.overhead='$OVERHEAD'", text)
        self.assertNotIn("set sqm.wan.overhead='0'", text)

    def test_sysctl_script_avoids_unavailable_fq_qdisc(self):
        script = (ROOT / 'packages/xr30-network-tuning/files/etc/uci-defaults/'
                          '99-xr30-network-tuning')
        text = script.read_text()
        # sch_fq is not built into this kernel, so writing default_qdisc=fq
        # would fail; the default is already fq_codel via an OpenWrt patch.
        self.assertNotIn('net.core.default_qdisc = fq\n', text)
        self.assertIn('net.ipv4.tcp_congestion_control = bbr', text)
        self.assertIn('vm.swappiness = 10', text)
        self.assertIn('net.ipv4.ip_local_port_range', text)
        # Longer UDP timeouts keep game/accelerator NAT mappings alive.
        self.assertIn('nf_conntrack_udp_timeout', text)
        self.assertIn('nf_conntrack_udp_timeout_stream', text)
        # Forbidden knobs must never appear as real settings.
        for bad in ('flow_offloading', 'tcp_fastopen'):
            self.assertNotRegex(text, rf'(?m)^\s*{bad}\s*=')

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
