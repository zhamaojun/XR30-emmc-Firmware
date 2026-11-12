# Development progress — evidence log

Date: 2026-11-13
Agent: DSH (not yet run against this package)

## What is known
- Existing Star-Song-derived V3 overlay was delivered with static script checks in an earlier step.
- Current physical router is running the original author's 21.02 image on `cmcc,rax3000m-emmc`, p4 kernel 32MiB / p5 rootfs 2GiB.
- No actual GitHub Actions build of this new overlay, router flash test, or hardware test is claimed here.

## Session log (agent should append real results)
| Time | Branch / Commit | Action | Evidence / URL | Result | Next step |
| --- | --- | --- | --- | --- | --- |
| 2026-11-13 03:10 | main (local, pre-push) | Installed DSH overlay into `D:\Documents\DSH\XR30固件配置`, ran doctor + unit tests | doctor PASS; 5 tests OK | Baseline static checks pass | Fork + CI |
| 2026-11-13 03:16 | main `4b8cde3` | Pushed overlay to owner's fork `zhamaojun/Actions-rax3000z-emmc`; GitHub registered `build-xr30-custom.yml` | https://github.com/zhamaojun/Actions-rax3000z-emmc/commit/4b8cde358a936bf3c2a7bd17b0d89902f63766b6 | Workflow active in Actions | Dispatch baseline |
| 2026-11-13 03:19 | main `4b8cde3` | Dispatched `baseline`, `source_ref=ab766…` | https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43289150610 | **FAILED** at `Generate profile config`: `ERROR: Forbidden packages still selected: docker, dockerd, iptables-mod-extra, iptables-mod-tproxy, kmod-ifb, kmod-ipt-nat, kmod-tun` | Fix package sets |
| 2026-11-13 03:27 | `feat/fix-baseline-package-sets` | Root cause: `kmod-ipt-nat` is a `firewall` base dependency, `kmod-ifb` is a `luci-app-eqos-mtk` dependency; author config left `luci-app-docker`, `v2raya`, `xray-core`, `zerotier` enabled, which pull `docker`/`dockerd`/`iptables-mod-*`/`kmod-tun`. Moved base deps to COMMON, removed leftover runtimes, added regression test | doctor PASS; 5 unit tests OK (baseline 464, performance 483, full 489 packages) | Local static verification passes | Rerun baseline CI |

## Build evidence (agent should fill after CI)
- Source SHA: `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd` (first baseline attempt; pins the version the router currently runs)
- Package feeds SHAs: pending first successful build
- OpenClash SHA: n/a for baseline
- iStore SHA: n/a for baseline
- Profile: baseline
- CI URL: https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43289150610 (failed run #1)
- First failed step / exact root cause: `Generate profile config` → `make defconfig` re-enabled base/author leftovers (see session log)
- Image SHA256:
- Kernel extracted bytes:
- Root extracted bytes:
- Supported devices metadata:
- Package manifest:
- Router flash: **NOT authorized**
