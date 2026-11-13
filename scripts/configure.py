#!/usr/bin/env python3
"""Transform the author's large .config with explicit, audited package choices.

This tool does NOT modify hardware partitions, EEPROM, or the router itself.
"""
import argparse
import pathlib
import re
import sys

COMMON = {
    "kmod-mediatek_hnat", "luci-app-mtwifi-cfg", "luci-app-eqos-mtk",
    "luci-app-turboacc-mtk", "luci-app-upnp", "luci-app-diskman",
    "luci-app-ttyd", "luci-compat", "dnsmasq-full", "ca-bundle",
    "curl", "htop",
    # Base-system dependencies: firewall (kmod-ipt-nat) and MTK eQoS
    # (kmod-ifb). make defconfig always re-selects these; treating them as
    # performance-only packages makes every baseline run fail verification.
    "kmod-ipt-nat", "kmod-ifb",
}
PERFORMANCE = {
    "luci-app-openclash", "bash", "ruby", "ruby-yaml", "ip-full",
    "ipset", "unzip", "iptables-mod-tproxy", "iptables-mod-extra",
    "kmod-tun",
    "smartdns", "luci-app-smartdns",
    "wireguard-tools", "kmod-wireguard", "luci-app-wireguard",
    "docker", "dockerd", "luci-app-dockerman", "luci-lib-docker",
    # Spread NIC interrupts across both A53 cores; Docker and OpenClash on a
    # 2-core SoC otherwise pin most softirq work to CPU0.
    "irqbalance",
    # Conservative, reversible sysctl tuning (buffers/backlog/local BBR).
    # Never enables flow-offload, qdisc changes or TCP Fast Open.
    "xr30-network-tuning",
}
FULL = {
    "adguardhome", "tailscale", "luci-app-store",
    "luci-app-sqm", "sqm-scripts", "kmod-sched-cake",
    # LuCI for the AdGuard Home binary above (kenzok8, pinned, Lua/CBI).
    # It must NOT bundle a second adguardhome binary; see custom_prepare.sh.
    "luci-app-adguardhome",
    # In-tree Lua/CBI page; the upstream luci-app-tailscale is JS-view based
    # and cannot render on the Lua LuCI shipped with 21.02.
    "luci-app-tailscale-lite",
    # Operational visibility and recovery helpers.
    "luci-app-statistics", "luci-app-vnstat2",
    "luci-app-watchcat", "luci-app-wol",
}
# Remove overlapping/obsolete services from the author's very large baseline.
REMOVE = {
    "luci-app-turboacc", "luci-app-ssr-plus", "luci-app-v2raya",
    "luci-app-zerotier", "luci-app-docker",
    # Author's config also enabled the proxy/VPN runtimes themselves; they
    # pull kmod-tun, iptables-mod-tproxy and iptables-mod-extra into baseline.
    "v2raya", "xray-core", "zerotier",
    "luci-app-adbyby-plus", "luci-app-accesscontrol",
    "luci-app-airplay2", "luci-app-shairplay", "luci-app-autoreboot",
    "luci-app-ramfree", "luci-app-guest-wifi", "luci-app-socat",
    "luci-app-usb-printer", "luci-app-filetransfer",
}
# Profiles deliberately install SQM but NEVER automatically enable it.
# The router must choose hardware HNAT or full-path CAKE at runtime.
PROFILE = {
    "baseline": COMMON,
    "performance": COMMON | PERFORMANCE,
    "full": COMMON | PERFORMANCE | FULL,
}
PATTERN = re.compile(r"^(?:CONFIG_PACKAGE_|# CONFIG_PACKAGE_)([^=\s]+)(?:=[ym]| is not set)$")

# Target device selection.
#
# We build the *native* XR30 eMMC target that upstream added after our old pin,
# because it carries the XR30 white LED (GPIO34) in its own DTSI and therefore
# needs no LED patch. Its stock DTS runs the eMMC at 52 MHz, which the author's
# README warns can cause I/O errors or a non-booting device on marginal flash;
# scripts/patch_xr30_target.py pins it back to 26 MHz (what this unit has always
# run). The legacy target is kept below so a rollback stays a one-line change.
TARGET_DEVICE = "cmcc_xr30-emmc"
LEGACY_DEVICE = "cmcc_rax3000m-emmc"


def target_line(device):
    return f"CONFIG_TARGET_mediatek_mt7981_DEVICE_{device}=y"


def profile_line(device):
    return f'CONFIG_TARGET_PROFILE="DEVICE_{device}"'


def parse_enabled(text):
    return set(re.findall(r"^CONFIG_PACKAGE_([^=\n]+)=y$", text, flags=re.M))


def make_config(base, profile):
    if target_line(LEGACY_DEVICE) not in base:
        raise ValueError("Base is NOT the author's RAX3000M eMMC target config; refusing")
    desired = PROFILE[profile]
    # Everything not selected by our profile but explicitly unwanted is disabled.
    overrides = set(desired) | REMOVE | PERFORMANCE | FULL
    body = []
    for line in base.splitlines():
        # Drop the legacy target selection; we retarget explicitly below.
        if line == target_line(LEGACY_DEVICE) or line == profile_line(LEGACY_DEVICE):
            continue
        if (m := PATTERN.match(line)) and m.group(1) in overrides:
            continue
        body.append(line)
    body.append(target_line(TARGET_DEVICE))
    body.append(profile_line(TARGET_DEVICE))
    body += [f"CONFIG_PACKAGE_{pkg}=y" for pkg in sorted(desired)]
    body += [f"# CONFIG_PACKAGE_{pkg} is not set" for pkg in sorted(overrides - desired)]
    return "\n".join(body) + "\n"


def verify_config(config, profile):
    enabled = parse_enabled(config)
    missing = sorted(PROFILE[profile] - enabled)
    if target_line(TARGET_DEVICE) not in config:
        raise ValueError(f"Wrong target after make defconfig: expected {TARGET_DEVICE}")
    if target_line(LEGACY_DEVICE) in config:
        raise ValueError(f"Legacy target {LEGACY_DEVICE} still selected; retargeting failed")
    if missing:
        raise ValueError("Selected packages absent after make defconfig; feeds/Kconfig incompatible: " + ", ".join(missing))
    forbidden = sorted((REMOVE | (PERFORMANCE | FULL) - PROFILE[profile]) & enabled)
    if forbidden:
        raise ValueError("Forbidden packages still selected: " + ", ".join(forbidden))
    print(f"OK: {profile}; {len(enabled)} enabled packages, all {len(PROFILE[profile])} required selections present.")
    print("NOTICE: this validates Kconfig only, not successful compilation or device functionality.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", type=pathlib.Path)
    p.add_argument("--output", type=pathlib.Path)
    p.add_argument("--verify", type=pathlib.Path)
    p.add_argument("--profile", required=True, choices=PROFILE)
    args = p.parse_args()
    if args.verify:
        verify_config(args.verify.read_text(), args.profile)
    else:
        if not args.base or not args.output:
            p.error("--base and --output are needed for generation")
        args.output.write_text(make_config(args.base.read_text(), args.profile))
        print("Generated", args.output)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
