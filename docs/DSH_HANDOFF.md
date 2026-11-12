# DSH handoff — XR30 project

## Goal and status
User wants DeepSeek Harness to autonomously continue the GitHub Actions-based custom firmware from existing Star-Song sources. The user has already booted the original author's image and confirmed `cmcc,rax3000m-emmc`. No immediate flashing, hardware access, or root password action. Agent goal is **reproducible CI builds with evidence**.

## Existing verified device facts
- Version: ImmortalWrt 21.02-SNAPSHOT r20571-ab766cbcb0, mediatek/mt7981.
- Board: `cmcc,rax3000m-emmc`; reported model `CMCC RAX3000M eMMC version`, even though chassis is RAX3000Z Enhanced XR30.
- Boot args: `root=PARTLABEL=rootfs rootwait rootfstype=squashfs,f2fs`.
- GPT: p1 `u-boot-env` 512K; p2 `factory` 2M; p3 `fip` 2M; p4 `kernel` 32M; p5 `rootfs` 2G; p6 ext4 55.1G.
- p5 `/rom` squashfs, loop-mounted f2fs overlay; p6 has ext4 and was not mounted in supplied output.
- User has custom U-Boot and boots known-good author's image; no evidence of production FIT / dual A-B boot slot.

## Existing overlay
`.github/workflows/build-xr30-custom.yml`: builds 3 profiles with GitHub Actions; checks some Kconfig/LED and collects artifacts; **not yet proven to complete actual CI**.
`scripts/configure.py`: profile selection but starts from author's broad 2024 .config; may retain unwanted optional packages, so `baseline` is not yet proven minimal.
`scripts/custom_prepare.sh`: obtains OpenClash sources on a floating branch; `iStore` added as feed with no pinned revision.
`scripts/patch_led.py`: handles old/new device-tree layout; old baseline requires external source file from original Fork.
`scripts/firmware_preflight.py`: offline partition-vs-image checks; no router-writing actions.

## Top issues to solve, in order
1. **Local inventory**: verify original Fork has author DTSI, `.config`, workflows; inspect the author's package targets and current upstream changes. Keep precise source/feeds SHAs. Check `scripts/dsh_project_doctor.py` + `python -m unittest discover -s tests -v`.
2. **Baseline reproducibility**: pin a known source SHA (start with `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`) and compatible feeds. Check missing packages, host dependencies, limitations of GitHub Actions Ubuntu 22.04. Ensure `mt7981-cmcc-rax3000m-emmc.dts` uses 26MHz and only XR30 white LED GPIO34 changes. Fix upstream layout drift fail-closed.
3. **Profile contents**: baseline MTK HNAT/mtwifi/MTK eQoS only (plus minimum tools); performance OpenClash + SmartDNS + WireGuard + Docker/Dockerman; full adds AdGuard Home + Tailscale + SQM/CAKE + iStore. Distinguish installed package, actual binary, runtime service and web UI. Kernel 5.4 iptables compatibility is a gate. Start with baseline. Avoid static package conflicts (e.g. firewall4/nftables 23+ vs current firewall/iptables), DNS :53 port contention, QoS+HNAT double shaping, Tailscale Go toolchain version, iStore repo ABI drift.
4. **CI actions**: run baseline, analyze exact first failure, targeted fix. Once baseline CI produces valid sysupgrade *tar-based image*, verify extracted kernel <= p4 32MiB and root <= p5 2GiB, correct compatible device metadata and SHA256; then performance and full. Keep hashes and manifest; never trust image basename alone.
5. **OpenClash runtime**: ensure separately bundled / downloadable Mihomo core version matches aarch64 and libc; do NOT confuse front-end with runnable core. DNS chain and TPROXY dependencies to be tested offline/CI; no live router modification.
6. **Documentation**: update `docs/DSH_PROGRESS.md` with CI links, source hashes, package bill, log summary, discovered blockers, next steps; produce clear comparison and recommended profile.

## Safety gates
- Do not execute `sysupgrade -F`, `sysupgrade`, `mtd`, `dd of=/dev/mmc*`, `fw_setenv`, `ubiformat`, `mkfs`, `parted`, `sgdisk` on router. Do not SSH to device unless separate explicit permission for **read-only audit** is granted.
- Build workflow may write its ephemeral Ubuntu runner, but never a router or user data partition.
- Do not mix default source branches with conflicting package feeds or force firmware metadata to pass.
- A successful CI compilation is not a successful flash nor a tested hardware performance result.
- Keep V3 overlay backups and current known-good author's release available separately.

## No-loop debug policy
- No arbitrary 30-minute/30-call global stop. Continue as long as steps produce progress.
- Before a repeat: note changed code/config, identify why the next attempt may differ. Identical failure twice without meaningful change -> stop that retry path and investigate.
- Do not successively retry `make -jN` / `-j1` without diagnostics. Prefer smallest relevant Make target, package, host dependency or feed verification.

## Handoff completion format
1. File changes and exact commit IDs.
2. Build profile, source and feeds SHAs, action run link, pass/fail.
3. Image inventory and extracted kernel/root sizes versus p4/p5.
4. Component matrix installed vs unresolved; detected conflicts.
5. Next safe step (no flash without explicit authorization).
