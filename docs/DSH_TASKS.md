# DSH task board (unverified until a human or CI confirms)

## Phase 0 — Safe ingestion
- [ ] Confirm working directory is owner's Fork, not upstream author's repo.
- [ ] Confirm existing repo files and XR30 baseline author sources are present.
- [ ] Run local doctor and unit tests. Document outputs.
- [ ] Create a feature branch; record clean baseline and source SHA.

## Phase 1 — Basic build
- [ ] Fix static bugs and compatibility of 2024 source pin + package feeds.
- [ ] Ensure XR30 white LED GPIO34 and eMMC 26 MHz.
- [ ] Run baseline GitHub Actions on owner's Fork. No automatic public release.
- [ ] Collect exact upstream + feed hashes, package manifest, CI logs.
- [ ] Inspect sysupgrade metadata and p4/p5 *uncompressed* tar contents; FAIL if kernel >32MiB or root >2GiB.

## Phase 2 — Performance build
- [ ] OpenClash LuCI and matching core + dependencies; verify actual presence.
- [ ] SmartDNS with deterministic DNS topology and no automatic port conflict.
- [ ] WireGuard userspace/kernel deps in Linux 5.4.
- [ ] Docker/Dockerman availability; p6 installation is future manual runtime work only.
- [ ] HNAT, MTK eQoS and non-double NAT acceleration selection.
- [ ] Run performance CI, capture evidence.

## Phase 3 — Full build
- [ ] AdGuard Home package works with legacy toolchain.
- [ ] Tailscale version/Go toolchain compatible, no unverified binary assumptions.
- [ ] iStore core/feeds pinned and compatible; do not assume marketplace binaries compatible.
- [ ] SQM/CAKE installed but disabled by default, no automatic HNAT conflict.
- [ ] Run full CI; investigate first root-cause error, update task status.

## Phase 4 — Preflash report only
- [ ] Compare board device ID `cmcc,rax3000m-emmc`, image metadata and partition fit.
- [ ] Document which services will start automatically and defaults for ports/DNS/QoS.
- [ ] Provide rollback instructions *without executing them*.
- [ ] Wait for owner to separately approve any router access or flashing.
