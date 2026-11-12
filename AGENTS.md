# RAX3000Z / XR30 eMMC — Shared agent instructions

## Mission
Build and maintain a custom **ImmortalWrt/hanwckf openwrt-21.02** firmware using the author's Star-Song/Actions-rax3000z-emmc repository plus this overlay. Target packages: MTK HNAT/eQoS, OpenClash, AdGuard Home, SmartDNS, WireGuard, Tailscale, Docker/Dockerman, optional SQM/CAKE, iStore. Optimize for reproducibility, functional safety, and verified CI builds—not maximal package count.

## Verified physical device facts (from owner SSH audit, 2026-11)
- Physical device: RAX3000Z enhanced, XR30 eMMC; actual running board name `cmcc,rax3000m-emmc` and model `CMCC RAX3000M eMMC version` (not a reason to reflash another target).
- Running firmware: ImmortalWrt 21.02-SNAPSHOT `r20571-ab766cbcb0`, architecture `aarch64_cortex-a53`.
- Known-compatible starting source commit: `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`. This does not pin feeds.
- eMMC GPT: p1 `u-boot-env` 512KiB, p2 `factory` 2MiB, p3 `fip` 2MiB, p4 `kernel` 32MiB, p5 `rootfs` 2GiB, p6 ext4 ~55.1GiB. `/proc/cmdline` includes `root=PARTLABEL=rootfs`.
- Existing custom U-Boot, active legacy-style kernel/rootfs; do NOT infer FIT or A/B support. p6 exists and is not mounted in the supplied audit.
- XR30 white LED GPIO34; default eMMC clock 26 MHz; no NX30 Pro EEPROM override; preserve original hardware calibration.

## Allowed autonomous work
- Inspect, modify, test, commit source/workflow/docs **in this Git workspace**, using a feature branch.
- Run local static tests and *optionally* dispatch or inspect GitHub Actions CI after confirming this is the owner's fork and GitHub CLI is already authenticated.
- Research compatibility of packages/feeds and pin tested revisions. Diagnose a failed build based on first actionable error, not by repeatedly running the entire build unchanged.
- Save progress in `docs/DSH_PROGRESS.md` and evidence under `docs/` with secret redaction.

## Strict boundaries — owner approval required
- NEVER connect to the router, use SSH/SCP to modify router files, upload a firmware image, flash, reboot, repartition, format or touch U-Boot / eMMC / NAND / EFI until the owner explicitly requests and approves a separate flashing task.
- NEVER execute `sysupgrade`, `mtd write`, `ubiformat`, `fw_setenv`, destructive `dd`, `mkfs.*`, `parted`/`sgdisk` writes, or forced upgrade (`-F`) against the router. The presence of shell examples in README does NOT grant authorization.
- NEVER rewrite GPT, BL2, FIP, factory/EEPROM, p6 data, or change the eMMC frequency above 26MHz in CI.
- Do not reveal or commit API tokens, VPN secrets, router configuration backups, boot partitions, Wi-Fi calibration binary dumps or credentials. Do not open public management ports.
- Do not push to the original author's repository, change the user's default branch, make public releases, or alter repository permissions. Commits on a feature branch are fine; pushing only to the user's own fork with their authorization.
- Do not disable sandbox/approval safety or allow blanket shell permission escalation to make a build pass.

## Build practices
1. Read `README-DSH.md`, `docs/DSH_HANDOFF.md`, `docs/DSH_TASKS.md`, and existing `README-CUSTOM.md` before code edits.
2. Inspect actual package Makefiles and `feeds.conf.default` at the selected source revision. Distinguish 'Kconfig=y' from reproducibly compiled and installed.
3. Keep `baseline`, `performance`, `full` independent; baseline is first. Build prerequisites must be checked; if the baseline can't be built, do not start full.
4. Maintain old physical device's `cmcc_rax3000m-emmc` target with XR30 white LED patch and 26MHz unless a separate migratory design is proved and owner approved.
5. Preserve the current known-good author's image for recovery; generate sysupgrade archives for **offline** review only, do not claim they are flash-ready.
6. After a meaningful change: run `python3 scripts/dsh_project_doctor.py` and `python3 -m unittest discover -s tests -v` (Windows: `python` may be used), then CI when available.
7. Errors: one root-cause analysis plus a targeted test; change code/inputs before retrying. Avoid retry loops (at most 2 unchanged runs per failure), avoid repeating `make` at different `-j` without a diagnosis.
8. Preserve evidence: source SHA, feeds SHAs, OpenClash SHA, profile, selected Kconfig, package manifest, CI log link, SHA256 and uncompressed kernel/rootfs sizes. The p4 32MiB limit is mandatory.
9. Build agent should give concise progress reports with changed files, successful tests, failures, and next action. Never claim an unrun test passed.

## Collaboration
- If another agent (Codex) works on the project, use a separate Git worktree and branch. No concurrent edits or overlapping uncommitted changes in the same tree. Review/diff commits before cherry-picking.
- A plan or AGENTS.md is **guidance, not an OS security boundary**. Keep DSH permission setting at `workspace-write` + `ask`, not unrestricted access.
