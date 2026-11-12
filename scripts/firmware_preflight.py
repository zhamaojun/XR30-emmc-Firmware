#!/usr/bin/env python3
"""Offline READ-ONLY XR30 eMMC sysupgrade preflight. Never invokes flashing commands.

Input 1: stdout captured by scripts/router_audit_readonly.sh on the actual router.
Input 2: self-built sysupgrade.bin tar image. Binary metadata/fwtool and U-Boot
compatibility MUST be checked separately: a PASS here is NOT flash approval.
"""
import argparse
import pathlib
import sys
import tarfile

TARGET_ALIASES = {
    'cmcc,rax3000m-emmc': 'rax3000m-emmc',
    'cmcc,xr30-emmc': 'xr30-emmc',
}


def load_audit(path):
    lines = path.read_text(errors='replace').splitlines()
    fields = [x.split('|') for x in lines if x.startswith('XR30_')]
    if not any(x[:2] == ['XR30_AUDIT_COMPLETE', 'YES'] for x in fields):
        raise ValueError('Audit incomplete or invalid')
    board = next((x[1] for x in fields if x[0] == 'XR30_BOARD' and len(x) >= 2), None)
    parts = {}
    duplicates = set()
    for x in fields:
        if x[0] != 'XR30_PART' or len(x) < 4 or not x[1]:
            continue
        try:
            size = int(x[3])
        except ValueError:
            continue
        if x[1] in parts:
            duplicates.add(x[1])
        parts[x[1]] = (x[2], size)
    env = {x[1]: x[2] for x in fields if x[0] == 'XR30_BOOTENV' and len(x) >= 3}
    bootargs = next((x[1] for x in fields if x[0] == 'XR30_BOOTARGS' and len(x) >= 2), '')
    return board, parts, env, bootargs, duplicates


def inspect_tar(image):
    if not image.is_file():
        raise ValueError(f'Firmware does not exist: {image}')
    if image.stat().st_size < 4096:
        raise ValueError('Firmware suspiciously small')
    try:
        with tarfile.open(image, mode='r:') as tar:
            files = [m for m in tar.getmembers() if m.isfile()]
    except (tarfile.TarError, OSError) as exc:
        raise ValueError(f'Not a supported sysupgrade TAR image: {exc}') from exc
    picked = {}
    for wanted in ('kernel', 'root'):
        candidates = [m for m in files if m.name.startswith('sysupgrade-') and m.name.endswith('/' + wanted)]
        if len(candidates) != 1:
            raise ValueError(f'Expected one sysupgrade-*/{wanted} entry, found {len(candidates)}')
        picked[wanted] = (candidates[0].name, candidates[0].size)
    dirs = {x.split('/')[0] for x, _ in picked.values()}
    if len(dirs) != 1:
        raise ValueError('Kernel and rootfs belong to different sysupgrade directories')
    return picked


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--audit', required=True, type=pathlib.Path)
    ap.add_argument('--image', required=True, type=pathlib.Path)
    ap.add_argument('--target', choices=sorted(TARGET_ALIASES), required=True,
                    help='Target declared by your build .config (not what you wish device was)')
    args = ap.parse_args()
    errors = []
    warnings = []
    board, parts, env, bootargs, duplicates = load_audit(args.audit)
    entries = inspect_tar(args.image)
    print('Actual board:', board)
    print('Build target:', args.target)
    if board != args.target:
        errors.append('Running device board_name differs from build target: do NOT force-flash')
    if duplicates & {'kernel', 'rootfs'}:
        errors.append('Duplicate kernel/rootfs partition names; cannot select a unique destination')
    if TARGET_ALIASES[args.target] not in args.image.name:
        errors.append('Image filename does not identify the declared eMMC target; verify build selection')
    for image_part, partition, reserve_mb in [('kernel', 'kernel', 1), ('root', 'rootfs', 8)]:
        name, need = entries[image_part]
        print(f'Image {name}: {need:,} bytes')
        if partition not in parts:
            errors.append(f'Missing GPT PARTLABEL={partition}')
            continue
        dev, capacity = parts[partition]
        print(f'GPT {partition} (/dev/{dev}): {capacity:,} bytes')
        if capacity <= 0 or need + (reserve_mb * 1024 * 1024) > capacity:
            errors.append(f'{image_part} has insufficient capacity incl. conservative {reserve_mb}MiB reserve')
    if 'production' in parts:
        slot = env.get('dual_boot.current_slot')
        if slot == '1':
            errors.append('dual_boot.current_slot=1: FIT production slot may be active; legacy sysupgrade may update inactive kernel/rootfs')
        elif slot != '0':
            errors.append('Production partition exists; boot slot unknown (cannot prove legacy kernel/rootfs is active)')
    if 'PARTLABEL=production' in bootargs or 'root=/dev/mmcblk0p66' in bootargs:
        errors.append('Running root may use production/FIT layout rather than legacy rootfs')
    if not bootargs:
        warnings.append('Missing kernel bootargs; inspect actual boot path manually')
    warnings += [
        'This check does NOT parse fwtool metadata or U-Boot boot scripts; run sysupgrade -T and review metadata on actual firmware.',
        'No GPT/BL2/FIP/factory writing or backup occurs here.',
        'Actual upgrade may change overlay/config; back up to an external computer first.',
    ]
    print('\nPREFLIGHT RESULT:', 'BLOCKED' if errors else 'BASIC CHECKS PASSED (NOT FLASH APPROVAL)')
    for x in errors:
        print('BLOCKER:', x)
    for x in warnings:
        print('NOTE:', x)
    return 2 if errors else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print('PREFLIGHT ERROR:', exc, file=sys.stderr)
        sys.exit(2)
