# DSH task board (状态经 2026-11-13 只读全量审计核实)

## Phase 0 — Safe ingestion
- [x] Confirm working directory is owner's Fork, not upstream author's repo.（`origin`=zhamaojun fork，`upstream` 推送已禁用）
- [x] Confirm existing repo files and XR30 baseline author sources are present.
- [x] Run local doctor and unit tests. Document outputs.（doctor PASS；9 项单测 OK）
- [x] Create a feature branch; record clean baseline and source SHA.（`4b8cde3`；source pin `ab766cb`）

## Phase 1 — Basic build
- [x] Fix static bugs and compatibility of 2024 source pin + package feeds.（`4f09722` 修复 defconfig 重选作者遗留包）
- [x] Ensure XR30 white LED GPIO34 and eMMC 26 MHz.（上游 `ab766cb` DTS 核对一致；CI grep 26MHz 强制失败关闭）
- [x] Run baseline GitHub Actions on owner's Fork. No automatic public release.（run [43290704198](https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43290704198) success）
- [x] Collect exact upstream + feed hashes, package manifest, CI logs.（⚠ baseline 运行时 workflow 尚无 feeds-sha 记录，仅 `feeds.buildinfo` 短 SHA，见 `docs/DSH_PROGRESS.md` 基线条目；证据缺口已记录，暂不补跑）
- [x] Inspect sysupgrade metadata and p4/p5 *uncompressed* tar contents; FAIL if kernel >32MiB or root >2GiB.（kernel 3,612,842 B / root 57,720,832 B，本地门禁 PASS）

## Phase 2 — Performance build
- [x] OpenClash LuCI and matching core + dependencies; verify actual presence.（`luci-app-openclash 0.48.002`，OpenClash SHA `e553e82e…`；**core 内核不打包**，首次使用由 OpenClash 自行下载）
- [x] SmartDNS with deterministic DNS topology and no automatic port conflict.（`smartdns` + `luci-app-smartdns` 已编译；运行期端口/DNS 拓扑需上机只读确认，见 `docs/PREFLASH_REPORT.md` §4）
- [x] WireGuard userspace/kernel deps in Linux 5.4.（`kmod-wireguard 5.4.255-1`、`wireguard-tools` 在 manifest）
- [x] Docker/Dockerman availability; p6 installation is future manual runtime work only.（`docker`/`dockerd`/`luci-app-dockerman v0.5.13` 已编译；数据目录上机后手动指向 p6，rootfs 仅 2GiB）
- [x] HNAT, MTK eQoS and non-double NAT acceleration selection.（`kmod-mediatek_hnat`、`luci-app-eqos-mtk` 在全部三档）
- [x] Run performance CI, capture evidence.（run [43302919486](https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43302919486) success；kernel 3,614,110 B / root 87,412,736 B）

## Phase 3 — Full build
- [x] AdGuard Home package works with legacy toolchain.（`adguardhome 0.107.36-1` 编译通过；运行期未测）
- [x] Tailscale version/Go toolchain compatible, no unverified binary assumptions.（`tailscale 1.32.3-1` 编译通过）
- [x] iStore core/feeds pinned and compatible; do not assume marketplace binaries compatible.（`luci-app-store 0.2.1-r1` 编译通过，feed HEAD `a97ace34…` 已记录但**未锁定**；商店内下载的二进制与本 target 的兼容性不作保证）
- [x] SQM/CAKE installed but disabled by default, no automatic HNAT conflict.（`sqm-scripts 1.5.1-1`、`kmod-sched-cake 5.4.255-1`；默认无配置不启动；CAKE 与 HNAT 二选一需手动）
- [x] Run full CI; investigate first root-cause error, update task status.（run [43314936466](https://github.com/zhamaojun/Actions-rax3000z-emmc/actions/runs/43314936466) success；kernel 3,614,398 B / root 102,905,856 B）

## Phase 4 — Preflash report only
- [x] Compare board device ID `cmcc,rax3000m-emmc`, image metadata and partition fit.（`docs/PREFLASH_REPORT.md` §1–§2）
- [x] Document which services will start automatically and defaults for ports/DNS/QoS.（`docs/PREFLASH_REPORT.md` §4）
- [x] Provide rollback instructions *without executing them*.（`docs/PREFLASH_REPORT.md` §6）
- [ ] Wait for owner to separately approve any router access or flashing.（**当前状态：未授权，不执行任何上机/刷写操作**）

## 2026-11-13 只读全量审计结论
- 三档产物 SHA256 复算一致、尺寸门禁通过、设备标识/源 SHA/LED GPIO34/eMMC 26MHz 与上游 `ab766cb` 逐一核对一致；kmod ABI 全部为内核 5.4.255 系；禁选包零泄漏；仓库无硬编码密钥。详表见 `docs/PREFLASH_REPORT.md` §7。
- 已修复：main 分支跟踪上游仓库的配置错误；补丁 LED 标签不一致；本任务板与进度文档的证据缺口标注。
- 已知限制（不修复，仅记录）：feeds/OpenClash 未按已验证 SHA 锁定，重建会漂移；作者旧 workflow 保留 `permissions: write-all`（仅手动触发）；真实兼容性以单独授权的预刷机检查为准。
