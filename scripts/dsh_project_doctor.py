#!/usr/bin/env python3
"""Offline-only static checks for the DSH handoff overlay (NOT a build or flash test)."""
from pathlib import Path
import sys
import re

root = Path(__file__).resolve().parents[1]
errors = []

required = [
    'AGENTS.md', 'README-DSH.md', 'README-CUSTOM.md',
    'docs/DSH_HANDOFF.md', 'docs/DSH_TASKS.md', 'docs/DSH_START_PROMPT.md',
    'docs/verified-device-layout.md',
    '.github/workflows/build-xr30-custom.yml',
    'scripts/configure.py', 'scripts/custom_prepare.sh', 'scripts/patch_led.py',
    'scripts/patch_xr30_target.py',
    'scripts/firmware_preflight.py', 'scripts/verify_images.py',
    'configs/rax3000z-emmc.config', 'mt7981-cmcc-xr30-emmc.dtsi',
    # In-tree LuCI package: Lua/CBI Tailscale page for the Lua LuCI in 21.02.
    'packages/luci-app-tailscale-lite/Makefile',
    'packages/luci-app-tailscale-lite/luasrc/controller/tailscale.lua',
    'packages/luci-app-tailscale-lite/luasrc/model/cbi/tailscale/status.lua',
    'packages/luci-app-tailscale-lite/root/usr/share/rpcd/acl.d/luci-app-tailscale-lite.json',
    'packages/luci-app-tailscale-lite/root/etc/uci-defaults/90-luci-app-tailscale-lite',
    # Reversible network tuning.
    'packages/xr30-network-tuning/Makefile',
    'packages/xr30-network-tuning/files/etc/uci-defaults/99-xr30-network-tuning',
]
for name in required:
    if not (root / name).is_file():
        errors.append(f'Missing: {name} (original author repository may not have been merged)')

# The in-tree Tailscale page exists because upstream luci-app-tailscale is
# JS-view based and needs LuCI 22.03+. Shipping any .js there would silently
# produce a blank page on this 21.02 firmware.
in_tree_luci = root / 'packages/luci-app-tailscale-lite'
if in_tree_luci.is_dir():
    stray_js = sorted(p.name for p in in_tree_luci.rglob('*.js'))
    if stray_js:
        errors.append('luci-app-tailscale-lite must stay Lua-only; found: ' + ', '.join(stray_js))

# Third-party sources must be pinned by full commit SHA, not a branch head.
prep = root / 'scripts/custom_prepare.sh'
if prep.is_file():
    prep_text = prep.read_text(encoding='utf-8', errors='replace')
    if not re.search(r"KENZOK8_SHA='[0-9a-f]{40}'", prep_text):
        errors.append('custom_prepare.sh must pin the kenzok8 revision with a full 40-char SHA')
    if 'codeload.github.com' not in prep_text:
        errors.append('custom_prepare.sh should fetch pinned sources via codeload tarball')

cfg = root / 'configs/rax3000z-emmc.config'
if cfg.exists():
    t = cfg.read_text(encoding='utf-8', errors='replace')
    if 'CONFIG_TARGET_mediatek_mt7981_DEVICE_cmcc_rax3000m-emmc=y' not in t:
        errors.append('Wrong original config: cmcc_rax3000m-emmc target not enabled')

legacy = root / 'mt7981-cmcc-xr30-emmc.dtsi'
if legacy.exists():
    s = legacy.read_text(encoding='utf-8', errors='replace')
    if 'gpios = <&pio 34 GPIO_ACTIVE_LOW>;' not in s:
        errors.append('Missing XR30 white LED GPIO34 in author DTSI')

workflow = root / '.github/workflows/build-xr30-custom.yml'
if workflow.exists():
    y = workflow.read_text(encoding='utf-8')
    for expected in ['scripts/configure.py', 'scripts/patch_xr30_target.py', 'make download', 'make -j',
                     'baseline', 'performance', 'full',
                     'Apply XR30 target patches',
                     'Apply default LAN IP (fail-closed)',
                     'Verify third-party and in-tree package sources',
                     'kenzok8-source-sha.txt']:
        if expected not in y:
            errors.append('Workflow missing expected step: ' + expected)
    # The legacy LED patch must not be wired into the build any more; the
    # native target owns the LEDs. Keeping it unused is fine (rollback path).
    if 'scripts/patch_led.py' in y:
        errors.append('Workflow still invokes the legacy LED patch; native target should own LEDs')
    # Check no unintentional firmware flash on the CI runner.
    if re.search(r'(?m)^\s*run:\s*(?:ssh|sysupgrade|mtd\s+write)', y):
        errors.append('Suspicious flash-like workflow step')

for name in ['scripts/configure.py', 'scripts/patch_led.py', 'scripts/patch_xr30_target.py',
             'scripts/firmware_preflight.py', 'scripts/verify_images.py']:
    p=root/name
    if p.is_file():
        try:
            compile(p.read_bytes(), str(p), 'exec')
        except SyntaxError as exc:
            errors.append(f'Python syntax problem in {name}: {exc}')

if errors:
    for line in errors: print('FAIL:', line)
    print('Doctor: FAIL. Missing author source? Merge pack into own Fork before retrying.')
    sys.exit(1)
print('PASS: overlay and author files present; target/LED/workflow syntax checked statically.')
print('NOT checked: Linux dependency resolution, actual GitHub Actions build, images, router or flash.')
