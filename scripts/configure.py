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
}
PERFORMANCE = {
    "luci-app-openclash", "bash", "ruby", "ruby-yaml", "ip-full",
    "ipset", "unzip", "iptables-mod-tproxy", "iptables-mod-extra",
    "kmod-ipt-nat", "kmod-tun",
    "smartdns", "luci-app-smartdns",
    "wireguard-tools", "kmod-wireguard", "luci-app-wireguard",
    "docker", "dockerd", "luci-app-dockerman", "luci-lib-docker",
}
FULL = {
    "adguardhome", "tailscale", "luci-app-store",
    "luci-app-sqm", "sqm-scripts", "kmod-sched-cake", "kmod-ifb",
}
# Remove overlapping/obsolete services from the author's very large baseline.
REMOVE = {
    "luci-app-turboacc", "luci-app-ssr-plus", "luci-app-v2raya",
    "luci-app-zerotier", "luci-app-adbyby-plus", "luci-app-accesscontrol",
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


def parse_enabled(text):
    return set(re.findall(r"^CONFIG_PACKAGE_([^=\n]+)=y$", text, flags=re.M))


def make_config(base, profile):
    if "CONFIG_TARGET_mediatek_mt7981_DEVICE_cmcc_rax3000m-emmc=y" not in base:
        raise ValueError("Base is NOT the author's RAX3000M eMMC target config; refusing")
    desired = PROFILE[profile]
    # Everything not selected by our profile but explicitly unwanted is disabled.
    overrides = set(desired) | REMOVE | PERFORMANCE | FULL
    body = [line for line in base.splitlines() if not
            ((m := PATTERN.match(line)) and m.group(1) in overrides)]
    body += [f"CONFIG_PACKAGE_{pkg}=y" for pkg in sorted(desired)]
    body += [f"# CONFIG_PACKAGE_{pkg} is not set" for pkg in sorted(overrides - desired)]
    return "\n".join(body) + "\n"


def verify_config(config, profile):
    enabled = parse_enabled(config)
    missing = sorted(PROFILE[profile] - enabled)
    if "CONFIG_TARGET_mediatek_mt7981_DEVICE_cmcc_rax3000m-emmc=y" not in config:
        raise ValueError("Wrong target after make defconfig")
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
