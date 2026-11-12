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
    'scripts/firmware_preflight.py', 'scripts/verify_images.py',
    'configs/rax3000z-emmc.config', 'mt7981-cmcc-xr30-emmc.dtsi',
]
for name in required:
    if not (root / name).is_file():
        errors.append(f'Missing: {name} (original author repository may not have been merged)')

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
    for expected in ['scripts/configure.py', 'scripts/patch_led.py', 'make download', 'make -j', 'baseline', 'performance', 'full']:
        if expected not in y:
            errors.append('Workflow missing expected step: ' + expected)
    # Check no unintentional firmware flash on the CI runner.
    if re.search(r'(?m)^\s*run:\s*(?:ssh|sysupgrade|mtd\s+write)', y):
        errors.append('Suspicious flash-like workflow step')

for name in ['scripts/configure.py', 'scripts/patch_led.py', 'scripts/firmware_preflight.py', 'scripts/verify_images.py']:
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
