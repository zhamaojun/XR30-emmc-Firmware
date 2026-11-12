# RAX3000Z 增强版 XR30 eMMC — GitHub Actions 定制叠加包（实验性）

> 基于 Star-Song/Actions-rax3000z-emmc 的定制叠加包。**不是已经编译通过或验证过刷机的固件**。2026-11 核查，原作者构建基于 hanwckf 的 `openwrt-21.02`/Linux 5.4 分支；21.02 官方已 EOL。此项目只构建，不刷路由器、不更改 EEPROM、不写 eMMC 分区。

## 使用方式

1. 先 Fork：<https://github.com/Star-Song/Actions-rax3000z-emmc>。
2. 把本 ZIP 内的 `.github/workflows/build-xr30-custom.yml`、`scripts/*`、`docs/*`、`README-CUSTOM.md` 复制到 Fork 仓库相同路径，**保留原仓库**的 `configs/rax3000z-emmc.config` 和 `mt7981-cmcc-xr30-emmc.dtsi`。
3. GitHub → Actions → `XR30 eMMC - Custom ImmortalWrt (unverified)` → `Run workflow` → 首先选择 `baseline`。
4. `baseline` 成功后运行 `performance`，再运行 `full`。每个阶段都查看 Kconfig 检查、编译日志和 sha256 清单。
5. 请勿根据生成文件名直接刷机！必须核对实际 U-Boot、分区布局和镜像 header，再建立恢复方案。

## 三个构建配置

| Profile | 编入的功能 | 目标 |
|---|---|---|
| baseline | 原作者硬件驱动与 XR30 LED 补丁；MTK HNAT、MTK eQoS、MTK TurboACC、UPnP、磁盘与网页管理 | 优先确认硬件基础 |
| performance | baseline + OpenClash 前端、SmartDNS、WireGuard、Docker | 测试网络与容器依赖 |
| full | performance + AdGuardHome、Tailscale、iStore、SQM/CAKE（仅预装、不自动启用） | 尝试完整所需组件 |

**设备树适配特别提醒：** 2026-11 的 hanwckf 上游已将 RAX3000M 设备树重构为 `mt7981-cmcc-rax3000m.dtsi` 引用 `mt7981-cmcc-rax3000m-xr30.dtsi`。新源码必须**只替换 LED GPIO 和别名**，而不能用 2024 旧文件覆盖整份新版硬件定义。本包 `scripts/patch_led.py` 会识别两种布局，未知布局直接拒绝构建。

**没有默认加入 MosDNS、NATMap、Full-cone NAT hack、BBR、SFE。** MosDNS 与 SmartDNS 在方案里二选一；NATMap 的 22.03+ 包不能直接假定适配 21.02；额外的 NAT 优化只在验证过源代码和内核后加入。

## 为什么要分阶段

- **iStore** 声明 21.02 需要 luci-compat，但商店的所有二进制包不保证与这套特殊内核/驱动兼容。
- **Tailscale** 的旧 packages feed 可能依赖过时的 Go 工具链；须以实际编译日志为准。
- **OpenClash** 官方包是管理前端，Mihomo 内核可能需首次运行后下载；不能认为在固件编译时已经完整内置内核。
- **AdGuard Home** 只加入其服务端包（自带网页界面），不加入未经校验的第三方 LuCI 包。
- **SQM** 仅预装；没有自动配置 CAKE，也没有在工作流中更改 MTK HNAT 运行状态。
- **OpenClash / AGH / SmartDNS** 不做“启动即自动改 53 端口”的预置配置。首次开机请按下面端口规划手动设定。

## DNS 规划（不要同时抢占 53）

建议先只启用 dnsmasq + SmartDNS 验证解析：dnsmasq 监听 LAN:53，转发至 SmartDNS 127.0.0.1:6053；SmartDNS 不单独占 53。然后再选用一个统一的入口，若要 AdGuard 统计每台客户端，建议 AGH 监听 LAN:53、dnsmasq 改至其他本地端口，AGH 上游 SmartDNS:6053、内网域名回查 dnsmasq，并检查 DHCP 配置和 DNS 回环。OpenClash 需要根据 TUN/透明代理模式决定是否接管 DNS，避免多个进程重定向 53。**此处仅为部署规划，CI 不会自动改动路由器配置。**

## NAT 与加速规划

- MTK HNAT 适合直连流量，**不要同时在同一转发路径启用通用 flow-offloading/shortcut-fe**。
- OpenClash 透明代理的部分流量将不使用普通 HNAT 快速路径；应测试分流/直连比例。
- MTK eQoS 与 SQM/CAKE 属不同整形路径；不要同时对同一 WAN 叠加整形。如果必须全流量 CAKE，测试时按需关闭 HNAT。
- UPnP 可以给同一 NAT 边界内的应用协商端口映射，但**不能自动穿透运营商 CGNAT**。
- 若有公网 IP，建议优先采用精确静态转发、UPnP（限可信网段）或 WireGuard/Tailscale；不要随意开放全端口或使用 DMZ。

## 持续维护要求

1. `source_ref` 默认跟随上游 `openwrt-21.02`，因此**不会复现完全相同的源码**。首次成功后必须将上游 commit、OpenClash commit 和 feeds commit 全部锁定，并保存 CI 构建日志。
2. 当前 overlay 中 OpenClash、iStore feed 默认跟随上游活动分支，**并未锁版本**。该方案是持续集成模板而非可重复编译发布流水线。
3. 一旦 `make defconfig` 无法选中任何必需包，立即中止，不允许静默生成缺少插件的“成功”固件。
4. 不推荐以 21.02 长期公开暴露 WAN 管理页面；优先评估更高版本、安全补丁及硬件兼容性。

## 资料

- 原作者：<https://github.com/Star-Song/Actions-rax3000z-emmc>
- 上游源码：<https://github.com/hanwckf/immortalwrt-mt798x>
- OpenClash：<https://github.com/vernesong/OpenClash>
- iStore：<https://github.com/linkease/istore>
- SmartDNS：<https://github.com/pymumu/smartdns>
- 设备验证详见 `docs/testing.md`。

## 重要：已经刷自定义 U-Boot 的路由器不要直接刷本项目镜像

2026-11 额外核实：hanwckf `openwrt-21.02` 当前上游已有**原生** `cmcc_xr30-emmc` 目标，LED GPIO34 已包含；但原生 DTS 默认 **52MHz**，与本工程旧 `cmcc_rax3000m-emmc` + LED 补丁、26MHz 目标不同。当前工作流仍沿用作者旧编译目标（`cmcc,rax3000m-emmc` 元数据）以减少未经验证的变化；**如果现有设备报告 `cmcc,xr30-emmc`，停止使用该旧目标镜像，不要强刷。**

已添加 `docs/flash-safety-and-recovery.md`、`scripts/router_audit_readonly.sh` 和 `scripts/firmware_preflight.py`。这三个文件只做只读审计/离线预检，不会刷机。用户已刷自定义 U-Boot 但分区未知时，应先生成审计文件核对启动槽、分区容量与固件目标；否则不要执行 sysupgrade。

## 已获得实机审计：2026-11-13

用户已确认运行 `ImmortalWrt 21.02-SNAPSHOT r20571-ab766cbcb0`，`board_name=cmcc,rax3000m-emmc`，GPT 有 p4 `kernel` 32MiB、p5 `rootfs` 2GiB、p6 ext4 数据区 55.1GiB。当前 p6 未挂载，现有 `/opt` 仍在 p5 overlay。**请以 `docs/verified-device-layout.md` 为准**；已提供针对本次已确认分区的 `scripts/backup_known_xr30_readonly.sh`（只读 eMMC，备份写 /tmp RAM）。
