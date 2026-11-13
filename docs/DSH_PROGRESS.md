# Development progress — evidence log

Date: 2026-11-13
Agent: DSH (baseline CI verified 2026-11-13)

## What is known
- Existing Star-Song-derived V3 overlay was delivered with static script checks in an earlier step.
- Current physical router is running the original author's 21.02 image on `cmcc,rax3000m-emmc`, p4 kernel 32MiB / p5 rootfs 2GiB.
- Baseline GitHub Actions build succeeded (run 43290704198, see evidence below); no router flash or hardware test is claimed.

## Session log (agent should append real results)
| Time | Branch / Commit | Action | Evidence / URL | Result | Next step |
| --- | --- | --- | --- | --- | --- |
| 2026-11-13 03:10 | main (local, pre-push) | Installed DSH overlay into `D:\Documents\DSH\XR30固件配置`, ran doctor + unit tests | doctor PASS; 5 tests OK | Baseline static checks pass | Fork + CI |
| 2026-11-13 03:16 | main `4b8cde3` | Pushed overlay to owner's fork `zhamaojun/Actions-rax3000z-emmc`; GitHub registered `build-xr30-custom.yml` | https://github.com/zhamaojun/Actions-rax3000z-emmc/commit/4b8cde358a936bf3c2a7bd17b0d89902f63766b6 | Workflow active in Actions | Dispatch baseline |
| 2026-11-13 03:19 | main `4b8cde3` | Dispatched `baseline`, `source_ref=ab766…` | https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43289150610 | **FAILED** at `Generate profile config`: `ERROR: Forbidden packages still selected: docker, dockerd, iptables-mod-extra, iptables-mod-tproxy, kmod-ifb, kmod-ipt-nat, kmod-tun` | Fix package sets |
| 2026-11-13 03:27 | `feat/fix-baseline-package-sets` | Root cause: `kmod-ipt-nat` is a `firewall` base dependency, `kmod-ifb` is a `luci-app-eqos-mtk` dependency; author config left `luci-app-docker`, `v2raya`, `xray-core`, `zerotier` enabled, which pull `docker`/`dockerd`/`iptables-mod-*`/`kmod-tun`. Moved base deps to COMMON, removed leftover runtimes, added regression test | doctor PASS; 5 unit tests OK (baseline 464, performance 483, full 489 packages) | Local static verification passes | Rerun baseline CI |
| 2026-11-13 03:31 | `feat/fix-baseline-package-sets` `4f09722` | Baseline CI rerun #2 | https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43290704198 | Config stage PASS; download PASS; compile in progress | Wait for images |
| 2026-11-13 03:50 | `feat/ci-size-gate-and-feed-evidence` | Added p4/p5 size gate (kernel 32 MiB, rootfs 2 GiB) to `verify_images.py`; workflow now records per-feed commit SHAs and uploads `feeds-shas.txt` / OpenClash SHA | doctor PASS; 9 unit tests OK | Size gate ready for artifact audit | Apply gate to baseline artifact when run completes |
| 2026-11-13 03:58 | `feat/ci-size-gate-and-feed-evidence` | Found duplicate OpenClash risk: luci feed ships 0.45.141-beta while `custom_prepare.sh` clones upstream 0.48.002 into `package/`. Workflow now removes the feed copy for performance/full so the package name is defined once | — | Prepared for performance profile | Validate during performance build |
| 2026-11-13 04:35 | main `531337c` | Baseline run #2 succeeded; artifact `xr30-baseline-2` downloaded and audited with the new size gate | https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43290704198 | PASS: kernel 3,612,842 B ≤ 32 MiB, root 57,720,832 B ≤ 2 GiB; sysupgrade SHA256 `a77ecd98…`; manifest 427 packages | Dispatch performance |
| 2026-11-13 05:47 | main `ba9700a` | Performance run #3 succeeded; artifact `xr30-performance-3` downloaded and audited | https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43302919486 | PASS: kernel 3,614,110 B ≤ 32 MiB, root 87,412,736 B ≤ 2 GiB; sysupgrade SHA256 `57fab6c1…`; manifest 471 packages; OpenClash `e553e82e…` | Dispatch full |
| 2026-11-13 07:25 | main `03cb0d4` | Full run #4 succeeded; artifact `xr30-full-4` downloaded and audited | https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43314936466 | PASS: kernel 3,614,398 B ≤ 32 MiB, root 102,905,856 B ≤ 2 GiB; sysupgrade SHA256 `3e1ce2ec…`; manifest 493 packages; includes luci-app-store, adguardhome, tailscale, sqm/CAKE | All three profiles verified; flashing still NOT authorized |
| 2026-11-13 12:00 | `feat/independent-maintenance` | Independence from stopped upstream: removed `upstream` git remote; README/AGENTS/HANDOFF wording now states independent maintenance (author credited as history); added "future source re-pin" procedure to `docs/PREFLASH_REPORT.md` §8 | — | Local docs + remote config only; no build inputs changed | Owner-side: leave fork network + optional repo rename on GitHub |
| 2026-11-13 14:30 | `feat/custom-lan-ip` | Owner requested default LAN IP 192.168.2.1; added workflow input `lan_ip` (default `192.168.2.1`) with dotted-quad validation + fail-closed sed patch of `config_generate`; repo renamed to `XR30-emmc-Firmware` and fork network detached (owner, GitHub UI) | — | doctor PASS; 9 unit tests OK | Dispatch full rebuild with lan_ip=192.168.2.1 |
| 2026-11-13 16:15 | main `791d641` | Fixed LAN IP verification pattern (`ipad=${ipaddr:-"..."}` not `ipaddr='...'`); CI run 43382017385 succeeded; artifact `xr30-full-6` verified: SHA256 `992f99da…`, `lan-ip.txt` = 192.168.2.1 | https://github.com/zhamaojun/XR30-emmc-Firmware/actions/runs/43382017385 | PASS kernel 3,614,398 B / root 102,905,856 B; owner flashed via U-Boot, booted to `r0-ab766cb` | Post-flash menu review |
| 2026-11-13 18:40 | `feat/tailscale-agh-menus` | Post-flash UI gap work. Verified DiskMan deps were already complete (`parted`/`blkid`/`smartmontools` present) — earlier "smartctl missing" report was a package-name mistake. Added: `irqbalance` (performance+full), `luci-app-adguardhome` (kenzok8 pinned `8099fdd5…`, Lua/CBI, 21.02-compatible), in-tree `packages/luci-app-tailscale-lite` (Lua/CBI, because every upstream luci-app-tailscale is JS-view and needs 22.03+), plus `luci-app-statistics`/`vnstat2`/`watchcat`/`wol` | — | doctor PASS; 19 unit tests OK (incl. Lua structure check) | Rebuild full, reflash |

## 2026-11-13 LuCI compatibility finding (why Tailscale needed an in-tree package)
- Upstream `luci-app-tailscale` (asvow v1.1.1–v1.2.6, gw826943555, whzhni1) all ship
  `htdocs/luci-static/resources/view/tailscale/*.js` using `'require view'; return view.extend({...})`.
  That is LuCI 22.03+ client-side rendering; the Lua-based LuCI in 21.02 cannot execute it,
  so the menu entry would appear but the page would render blank.
- asvow's page also defaults to `fw_mode = nftables`, while this firmware uses iptables.
- `luci-app-adguardhome` (kenzok8) is genuinely Lua/CBI (`"type": "cbi"` in its menu.d) and
  its README states 21.02 compatibility, so it is safe here. It must not bundle a second
  AdGuard Home binary → `INCLUDE_binary` stays disabled; the workflow greps for that switch.
- Consequence: the firmware now ships its own `luci-app-tailscale-lite` Lua page, and the
  build fails closed if any `.js` appears in it or if the AGH menu turns into `"type": "view"`.

## Build evidence — baseline (verified)
- Source SHA: `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`
- Package feeds SHAs (from `feeds.buildinfo`): `packages e09f3c7d1`, `luci 5829eabba5`, `routing a9e4310`, `telephony 920fbc5` (full 40-char SHAs were not captured by this run; the workflow now records them)
- Evidence gap (2026-11-13 audit): this run predates the size-gate/feed-recording workflow (`91a3772`), so its artifact lacks `feeds-shas.txt` and its `image-inventory.txt` has no `RESULT: PASS` line; the p4/p5 sizes below were verified locally with the current `scripts/verify_images.py`. Owner decided not to re-run baseline just for evidence.
- OpenClash SHA: n/a for baseline
- iStore SHA: n/a for baseline
- Profile: baseline
- CI URL: https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43290704198 (success)
- First failed step / exact root cause (run #1): `Generate profile config` → `make defconfig` re-enabled base/author leftovers (fixed in `4f09722`)
- Image SHA256: `a77ecd983ae6071f7d36b8653e831fa5dc23e74ecea9410b34ba7a84e1a9138b` (sysupgrade)
- Kernel extracted bytes: `3,612,842`
- Root extracted bytes: `57,720,832`
- Supported devices metadata: target `cmcc_rax3000m-emmc`, model `CMCC RAX3000M eMMC version`, device `cmcc,rax3000m-emmc`
- Package manifest: `immortalwrt-mediatek-mt7981-baseline.manifest` (427 packages, in artifact)
- Version: `r0-ab766cb`
- Router flash: **NOT authorized**

## Build evidence — performance (verified)
- Source SHA: `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`
- Package feeds SHAs (`feeds-shas.txt`): `luci 5829eabba50ec0afa17d2ee486bc90dc15180c34`, `packages e09f3c7d1903cfe7f523e209ab3ec778013ba309`, `routing a9e43101bb726070cbf81b6225fc0625f4a4a5e5`, `telephony 920fbc5c0a2e4badf51bceff42e9a1e3eb693462`
- OpenClash SHA: `e553e82e01c697aefbe1555261a503f425e00ccd`
- iStore SHA: n/a for performance
- Profile: performance
- CI URL: https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43302919486 (success)
- Image SHA256: `57fab6c1d529d5d6624d8f8f030c863e9cc2f0e04c6bf984ba19417c42752f89` (sysupgrade)
- Kernel extracted bytes: `3,614,110`
- Root extracted bytes: `87,412,736`
- Supported devices metadata: target `cmcc_rax3000m-emmc`, model `CMCC RAX3000M eMMC version`, device `cmcc,rax3000m-emmc`
- Package manifest: `immortalwrt-mediatek-mt7981-performance.manifest` (471 packages, in artifact)
- Included: `luci-app-openclash`, `luci-app-smartdns`, `wireguard-tools`, `docker`, `dockerd`
- Version: `r0-ab766cb`
- Router flash: **NOT authorized**

## Build evidence — full (verified)
- Source SHA: `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`
- Package feeds SHAs (`feeds-shas.txt`): `istore a97ace34f2da358a015b094d326bba2697697f2e`, `luci 5829eabba50ec0afa17d2ee486bc90dc15180c34`, `packages e09f3c7d1903cfe7f523e209ab3ec778013ba309`, `routing a9e43101bb726070cbf81b6225fc0625f4a4a5e5`, `telephony 920fbc5c0a2e4badf51bceff42e9a1e3eb693462`
- OpenClash SHA: `e553e82e01c697aefbe1555261a503f425e00ccd`
- iStore SHA: `a97ace34f2da358a015b094d326bba2697697f2e`
- Profile: full
- CI URL: https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43314936466 (success)
- Image SHA256: `3e1ce2ec63b9318f04b16687cc72b5664446d9e13bbb7d39f482f93d37efc8a6` (sysupgrade)
- Kernel extracted bytes: `3,614,398`
- Root extracted bytes: `102,905,856`
- Supported devices metadata: target `cmcc_rax3000m-emmc`, model `CMCC RAX3000M eMMC version`, device `cmcc,rax3000m-emmc`
- Package manifest: `immortalwrt-mediatek-mt7981-full.manifest` (493 packages, in artifact)
- Verified selected: `luci-app-store`, `adguardhome`, `tailscale`, `luci-app-sqm`, `kmod-sched-cake`, `luci-app-openclash`, `docker`
- Version: `r0-ab766cb`
- Router flash: **NOT authorized**

## 2026-11-13 read-only full audit (no repo/device mutation during audit)
- Scope: git state, doctor + 9 unit tests, bash -n on all shell scripts, Python AST/import checks, artifact audit (SHA256 recompute, tar size gate, device ID, source/feed SHAs, manifest package presence/absence, kmod ABI), upstream DTS reconciliation at `ab766cb`, secret scan.
- All green except the fixed items below; full traffic-light table in `docs/PREFLASH_REPORT.md` §7.
- Fixes applied on `feat/audit-fixes-preflash-report`: `main` now tracks `origin/main` (was `upstream/main`); `patch_led.py` new-layout LED label unified to `rax3000m:white`; `docs/DSH_TASKS.md` checkboxes updated to verified state; baseline evidence gap documented; Phase 4 `docs/PREFLASH_REPORT.md` created.
- kmod note: `kmod-gpio-button-hotplug 5.4.255-3` and `kmod-conninfra 5.4.255+bbf588-1` are upstream package-release tags, NOT ABI drift (all kmods are kernel 5.4.255 builds).
- Still open (documented, not fixed): feeds/OpenClash follow branch heads (rebuilds drift; verified SHAs recorded but not pinned); author's legacy workflows keep `permissions: write-all` (manual dispatch only); baseline evidence gap (rerun declined by owner).
