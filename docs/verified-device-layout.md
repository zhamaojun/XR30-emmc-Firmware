# RAX3000Z 增强版 XR30 eMMC：根据 2026-11-13 实机日志确认的布局

## 实机确认（不是推测）

- 设备 `board_name`: `cmcc,rax3000m-emmc`，model `CMCC RAX3000M eMMC version`；这是作者采用的兼容目标，**不代表实物不是 RAX3000Z 增强版**。
- ImmortalWrt `21.02-SNAPSHOT`，`r20571-ab766cbcb0`，源码提交为 `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd` (2024-06-13)。
- 启动参数 `root=PARTLABEL=rootfs rootwait rootfstype=squashfs,f2fs`，运行中 `/dev/mmcblk0p5` 挂载 `/rom`，f2fs loop overlay 也来自 p5。
- 设备 GPT：

| 分区 | 起止 LBA | 容量 | PARTLABEL/类型 | 备注 |
| --- | --- | --- | --- | --- |
| p1 | 8192–9215 | 512KiB | u-boot-env | 要备份 |
| p2 | 9216–13311 | 2MiB | factory | 唯一设备射频校准/MAC数据，必须备份 |
| p3 | 13312–17407 | 2MiB | fip | U-Boot 第二阶段相关数据，必须备份 |
| p4 | 17408–82943 | 32MiB | kernel | sysupgrade 写入目标 |
| p5 | 82944–4178943 | 2GiB | rootfs, squashfs+F2FS overlay | sysupgrade 写入目标，配置可能丢失 |
| p6 | 4179968–119781375 | 55.1GiB | ext4，无 PARTLABEL | 非系统固件区，**目前没有挂载** |

磁盘共 119783424 扇区（57.12 GiB），与厂商标称的 64GB 容量是不同单位换算结果。

## 判断

1. **旧目标为第一版首选**：`CONFIG_TARGET_mediatek_mt7981_DEVICE_cmcc_rax3000m-emmc=y`，保留 XR30 白灯 GPIO34 补丁、eMMC 26MHz，默认使用原机 EEPROM。
2. 不要为了 LED 或软件插件，改 GPT 或重新写 `boot0`、`fip`。当前 p4/p5 与上游 `emmc_do_upgrade` 的 `kernel/rootfs` 名称匹配。
3. GPT 无 `production`、`kernel2`、`rootfs2`，且启动参数与实际挂载指向 p5，因此**正在使用 kernel/rootfs 这套系统**；但不能只凭 `fw_printenv` 某两个变量无输出就判断 U-Boot 没有其他启动能力。
4. **必须检查新镜像 TAR 内部的 kernel <=32MiB 且保留余量**，不能用整份 `sysupgrade.bin` 文件大小与 p4 比较；同样检查 root 大小与 p5 的 2GiB 限制。并对照镜像 supported_devices 与当前 board。
5. p6 ext4 是数据分区，当前挂载记录没有它；**不能据此声称 Docker 已使用 55GiB**。原来的 `/opt` 是 p5 overlay。后续若要将 Docker 数据移动到 p6，应先检查 p6 内容，再按 UUID 挂载、迁移，绝不重新 mkfs。
6. `sysupgrade -T` 是基本镜像元数据校验，**不是容量、引导链和 U-Boot 的完整测试**。自编固件通过后再测试，不要 `-F` 强刷。

## 优先级最高的安全修复

首次登录提示 `There is no root password defined`；应立即在路由器执行 `passwd`，切勿开放公网 SSH/LuCI，备份前务必完成。

## 安全备份（只读源设备）

执行本叠加包 `scripts/backup_known_xr30_readonly.sh`。脚本会严查 board、p1–p5 LABEL 和大小、eMMC 硬件 boot 设备及 /tmp 剩余 RAM，仅将只读数据复制到 `/tmp/xr30-critical-backup/`：

- 硬件 `boot0`、`boot1`、p1 u-boot-env、p2 factory、p3 fip、p4 kernel；
- GPT 首 34 扇区、末 33 扇区；
- `sysupgrade -b` 导出的配置、包列表、设备布局及 SHA256 清单。

**它不备份正在使用的 p5 rootfs/overlay，也不备份 p6 ext4；要完整恢复当前状态仍需保存原作者系统镜像或在离线维护环境下备份 p5，重要 p6 数据按普通文件备份。**

脚本不运行任何 `dd of=/dev/...`、`fw_setenv`、`mkfs`、`parted`、`sgdisk` 或 `sysupgrade` 刷写操作。`/tmp` 是路由器 RAM，重启后就会丢失；必须立刻用 WinSCP / SCP 下载到电脑，检查 `sha256sum -c SHA256SUMS.txt`，且不公开备份。

在 Windows 10/11 PowerShell（有 OpenSSH 客户端时）：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\Documents\XR30-Backup" | Out-Null
scp -r "root@192.168.6.1:/tmp/xr30-critical-backup" "$env:USERPROFILE\Documents\XR30-Backup\"
```

把示例 IP 替换成路由器实际 LAN IP（如不在 192.168.6.1）。PowerShell `scp` 传输文件本身是二进制安全的，不同于将 SSH 原始二进制直接重定向到 PowerShell 5.1 的 `>`。

## 构建记录

若想与当前运行设备源码版本接近，GitHub Actions `source_ref` 可先填入：

`ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`

先运行 baseline 固件生成及离线比对，不直接刷。21.02 的第三方 feeds 仍可能变化，旧源码提交并不能保证能通过当下所有包依赖编译。之后再单独评估移动上游分支和 performance/full 功能。

## 刷前最终检查

- 下载已有作者系统 sysupgrade 与校验值，以便恢复；确认 U-Boot Web 界面支持何种类型的镜像（不要为此改启动变量）。
- 保存上述关键启动分区及 factory；确认备份到本机，不只是 `/tmp`。
- 根据 `router_audit_readonly.sh` 导出的审计文件和新 `sysupgrade.bin` 运行 `firmware_preflight.py`，PASS 仅表示基本条件满足。
- 再运行 `sysupgrade -T /tmp/镜像名` 做不刷写检测；禁止 `-F` 强制绕过检查。
- 由于当前厂商固件复杂，升级前先确保有网线/有线电脑、已知 U-Boot 恢复入口、原作者可回退的镜像。
- 所有条件满足后才讨论实际 sysupgrade；不要直接在本阶段执行刷写命令。
