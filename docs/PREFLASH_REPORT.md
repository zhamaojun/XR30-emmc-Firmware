# XR30 eMMC 预刷机报告（仅报告，不构成刷机许可）

日期：2026-11-13 ｜ 范围：本仓库三档 CI 产物 vs 已核实的物理设备事实 ｜ **刷机：未授权，本报告不执行任何上机操作**

> 本报告把"编译成功"与"可以刷机"严格分开。以下所有 ✅ 只代表离线证据一致；任何 `sysupgrade` 前仍需按 §5 做上机只读检查，并取得用户对刷机动作的单独授权。

## 1. 设备身份比对

| 项目 | 物理设备（2026-11 只读审计） | 三档构建产物 | 判定 |
| --- | --- | --- | --- |
| board_name | `cmcc,rax3000m-emmc` | `profiles.json` / config.buildinfo 均为 `cmcc,rax3000m-emmc` | ✅ |
| 机型字符串 | `CMCC RAX3000M eMMC version` | DTS `model` 一致（上游 `ab766cb` 核对） | ✅ |
| 架构 | `aarch64_cortex-a53` | `aarch64_cortex-a53`（mediatek/mt7981） | ✅ |
| 启动方式 | `root=PARTLABEL=rootfs rootwait` | eMMC DTS bootargs 一致 | ✅ |
| 上游源码 | 当前固件 `r20571-ab766cbcb0` | 构建 pin `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`（同一 commit） | ✅ |
| 版本号 | — | `r0-ab766cb`（三档一致） | ✅ |

## 2. 分区适配（GPT 与尺寸门禁）

| 分区 | 容量 | 用途 | 产物占用 | 判定 |
| --- | --- | --- | --- | --- |
| p4 `kernel` | 32 MiB | 内核 | baseline 3,612,842 B / performance 3,614,110 B / full 3,614,398 B（≈3.4 MiB） | ✅ 余量 ≈28.5 MiB |
| p5 `rootfs` | 2 GiB | 根文件系统 | baseline 57,720,832 B / performance 87,412,736 B / full 102,905,856 B（≈98 MiB） | ✅ 余量 ≈1.9 GiB |
| p1/p2/p3（env/factory/fip） | — | 启动与校准 | 产物**不触碰** | ✅ |
| p6 ext4 ≈55.1 GiB | — | 数据（审计时未挂载） | 产物**不触碰**；Docker 数据目录建议上机后指向此处 | ✅ |

- `initramfs-kernel.bin`（93,252,794 B）**仅供 U-Boot/TFTP 内存引导救砖，严禁写入 p4**（超过 32 MiB 会直接毁掉分区表邻区）。
- 三档 SHA256 本地复算与记录一致，CI 内部 `sha256sums` 7/7 条目复核一致。

## 3. 硬件适配（DTS 对账，上游 `ab766cb`）

| 项目 | 结论 |
| --- | --- |
| XR30 白灯 GPIO34 | ✅ 本仓库 `mt7981-cmcc-xr30-emmc.dtsi` 与 CI `patch_led.py` 均为 GPIO34 白灯；与上游内联版逐行比对，除绿/蓝→白灯外零差异 |
| eMMC 频率 | ✅ 上游 eMMC DTS `max-frequency = <26000000>`（26 MHz）；CI 步骤 grep 不到即失败（fail-closed），三档均通过 |
| EEPROM/校准 | ✅ 无 NX30 Pro EEPROM 覆盖；`factory` 分区校准数据不动 |
| 内存/外设 | ✅ 512 MiB、mt7531 交换、HNAT、USB3 定义与上游一致 |
| kmod ABI | ✅ 三档 manifest 全部 kmod 为内核 `5.4.255` 系（`kmod-gpio-button-hotplug 5.4.255-3`、`kmod-conninfra 5.4.255+bbf588-1` 为上游包发行号差异，非 ABI 漂移） |

## 4. 默认服务与端口（编译态证据 + 上机待确认项）

| 服务 | 档位 | 编译态 | 上机后需只读确认（届时逐项核对，不擅自改） |
| --- | --- | --- | --- |
| LuCI (uhttpd) | 全部 | 内置 | 监听 80/443，仅 LAN |
| dnsmasq-full 2.85-1 | 全部 | 内置 | 53 端口；与 SmartDNS 的上下游关系 |
| SmartDNS 1.2023.42 | perf/full | 内置 | 默认端口（通常 5335/6053）不与 53 冲突 |
| OpenClash 0.48.002 | perf/full | LuCI 内置；**core 内核不打包** | 首次启动联网下载内核；未下载前不接管流量；默认不自动启用 |
| AdGuard Home 0.107.36-1 | full | 内置 | 初始化端口 3000、运行端口需配置后再启用，避免与 dnsmasq 抢 53 |
| WireGuard | perf/full | `kmod-wireguard 5.4.255-1` | 未配置不监听 |
| Tailscale 1.32.3-1 | full | 内置 | 未登录不启动连接 |
| Docker/Dockerman v0.5.13 | perf/full | 内置 | dockerd 数据目录改指 p6；防火墙 docker0 规则 |
| SQM/CAKE 1.5.1 | full | 内置，默认无配置不启动 | 与 HNAT 硬件加速二选一，不可同时期望生效 |
| iStore 0.2.1-r1 | full | 内置 | 商店二进制不保证适配本 target，安装前三思 |
| mtwifi-cfg / eQoS-MTK / HNAT | 全部 | 内置 | 无线校准来自 factory 分区，勿动 |

## 5. 上机前只读检查（将来经授权后执行，现在不做）

1. `scripts/router_audit_readonly.sh` 在路由器上跑一遍，输出存 PC。
2. `python3 scripts/firmware_preflight.py --audit <审计输出> --image <sysupgrade.bin> --target cmcc,rax3000m-emmc` 全绿。
3. `scripts/backup_known_xr30_readonly.sh` 备份 boot0/boot1/p1–p4/GPT/配置到 `/tmp` 并**立即下载到 PC**（/tmp 重启即失）。
4. `sysupgrade -T <image>` 仅在路由器上测试镜像元数据（不写闪存）。
5. 以上全部通过后，才轮到"是否刷写"的独立授权对话。

## 6. 回滚预案（仅文档，不执行）

- **sysupgrade 不保留配置回滚**：用作者原镜像（当前在跑的 `r20571-ab766cbcb0` 对应固件，需事先从作者 Releases/历史构建留存）走同样 sysupgrade 流程刷回。
- **变砖恢复**：U-Boot 下 TFTP 内存引导 `initramfs-kernel.bin`（93 MB，仅内存运行），进入后再 sysupgrade 已知好镜像。
- **最后手段**：p4/p5 的 dd 恢复依赖 §5.3 的备份文件；无备份不做任何 dd 写。
- 任何情况下不重写 GPT/BL2/FIP/factory，不调高 eMMC 频率。

## 7. 兼容性红绿灯（2026-11-13 只读全量审计）

| 维度 | 灯 | 说明 |
| --- | --- | --- |
| 设备身份/目标 | 🟢 | board/model/架构/源码 commit 全一致 |
| 分区尺寸 | 🟢 | p4/p5 余量充足；initramfs 已标注禁刷 |
| 硬件 DTS（LED/26MHz/校准） | 🟢 | 与上游 pin 逐行核对一致 |
| 包集完整性/禁选泄漏 | 🟢 | 三档 manifest 逐项核对；作者遗留代理包零泄漏 |
| kmod ABI | 🟢 | 全部 5.4.255 系 |
| 产物完整性 | 🟢 | SHA256 复算一致；CI sha256sums 7/7 |
| 安全边界 | 🟢 | 仓库无密钥；脚本无上机写操作；只推 fork |
| baseline 证据完整性 | 🟡 | feeds 仅短 SHA、inventory 无 RESULT 行（构建早于门禁改进）；已记录，用户同意暂不补跑 |
| feeds/OpenClash 复现性 | 🟡 | 跟踪分支头，重建会漂移；已验证 SHAs 已记录但未锁定 |
| 作者旧 workflow | 🟡 | `write-all` 权限，仅手动触发，保留未改 |
| 真实运行兼容性 | 🔴 未验证 | 从未上电运行；OpenClash core/SmartDNS 端口/Docker 存储/SQM-HNAT 均需上机只读确认 |
| 刷机授权 | 🔴 未授权 | 本报告不构成刷机许可 |
