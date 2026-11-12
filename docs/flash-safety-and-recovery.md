# XR30 eMMC：现有自定义 U-Boot 设备的升级前检查、备份与恢复（安全版）

**适用范围**：设备已安装第三方系统和自定义 U-Boot，但具体启动槽位、eMMC GPT 分区布局尚未知晓。本文没有自动刷机或分区修改动作。需要手工确认当前固件的实际 `board_name`、启动链及分区大小以后，才可确认镜像兼容性。

## 关键结论（2026-11 核查 hanwckf openwrt-21.02）

1. 旧 Star-Song 工程编译目标 `cmcc_rax3000m-emmc`，输出 `*rax3000m-emmc*squashfs-sysupgrade.bin`，通过替换 XR30 的 LED 配置实现 3000Z 增强版适配；镜像 metadata 的 `supported_devices` 仍可能是 `cmcc,rax3000m-emmc`，**不会因为灯变成白色就变成 `cmcc,xr30-emmc`**。
2. hanwckf 当前源码已经原生包含 `cmcc_xr30-emmc`，DTS 模型为 `CMCC XR30 eMMC version (RAX3000Z Enhanced version)`，LED 是 GPIO35/34；**原生目标 DTS 默认 52MHz**。若采用原生目标，应先改为 26MHz 及核查构建 target，不可拿原作者旧目标配置冒充原生 XR30 目标。
3. 21.02 `platform_do_upgrade()` 对 `cmcc,rax3000m-emmc`、`cmcc,xr30-emmc` 调用 `emmc_do_upgrade`，设置 `CI_KERNPART=kernel`、`CI_ROOTPART=rootfs`；实际 `emmc_upgrade_tar` 会把镜像内 `kernel`/`root` 写入按 GPT 分区名称查到的块设备。该函数没有自动检测容量是否足够，也不主动写 GPT/BL2/FIP；`-n` 不是保护分区的万能开关。
4. 部分 lgs2007m 自定义 U-Boot 存在双启动机制：`kernel/rootfs` 是 21.02 legacy 槽，`production` 是主线 FIT 槽；**仅凭自定义 U-Boot 无法知道当前启动哪一个**。当 `production` 是活动槽时，legacy sysupgrade 可能写入非活动槽，甚至被其他固件自己的升级脚本拒绝。
5. `sysupgrade -T` 是**必做但不充分**的测试：通常校验镜像 metadata/设备标识/基本文件格式，不检查所有分区容量、当前 U-Boot 启动逻辑及机型所有驱动。

## 第 1 步：完全只读地审计设备

从附件 `scripts/router_audit_readonly.sh` 复制到路由器 `/tmp/router_audit_readonly.sh`，运行：

```sh
sh /tmp/router_audit_readonly.sh > /tmp/xr30-audit.txt
cat /tmp/xr30-audit.txt
```

脚本只读取：设备识别、Linux 启动参数、eMMC `mmcblk0`、硬件 boot0/boot1 容量、`PARTLABEL` 与各分区大小、部分不涉及密码的 U-Boot 槽位变量和挂载点。**不调用 `dd of=`、`fw_setenv`、`mkfs`、`sgdisk`、`parted` 或升级命令。**

请保存审计结果到自己的电脑。公开分享之前检查输出是否包含 MAC、序列号等个人设备标识。不要分享完整 `fw_printenv` 输出、Wi-Fi 密码、VPN 密钥或带证书的配置。

### 决策表

| 发现 | 结论 |
|---|---|
| `board_name=cmcc,rax3000m-emmc`、GPT 有 `kernel/rootfs` 且启动走 rootfs | 可继续验证 Star-Song 旧目标的镜像 **但仍需查容量和 U-Boot** |
| `board_name=cmcc,xr30-emmc` | 旧 Star-Song 目标元数据不匹配；应另起原生 XR30 编译配置（26MHz）并验证 |
| GPT 只有 `production`，缺 `kernel/rootfs` | 不能直接套用这份 eMMC sysupgrade TAR |
| GPT 同时有 `kernel/rootfs` 与 `production`，当前 `dual_boot.current_slot=1` | 先核实活动 FIT 槽；不能以升级旧系统的方式更新活动 FIT 固件 |
| `rootfs` 或 `kernel` 分区装不下新固件 | **禁止写入**；不要为了硬刷而 `-F` |
| 未知厂商定制 U-Boot/环境变量/文件格式 | 暂不刷机，先保留当前可启动固件与 U-Boot 恢复方式 |

## 第 2 步：备份（始终保存到路由器以外）

### 2.1 保存可恢复的配置与软件清单

在**路由器 SSH** 中执行：

```sh
umask 077
sysupgrade -l > /tmp/xr30-backup-file-list.txt
sysupgrade -b /tmp/xr30-config-backup.tar.gz
opkg list-installed > /tmp/xr30-installed-packages.txt 2>/dev/null || true
ls -lh /tmp/xr30-* 
```

然后通过 WinSCP/SCP 下载到电脑。**这只是配置备份，不是引导、EEPROM 或 GPT 备份**。config archive 可能包含敏感口令/密钥，请不要提交到 GitHub 或群组。跨固件分支升级不要直接完整还原旧配置。

### 2.2 强烈建议：从 Windows 的 WSL 直接流式备份 eMMC（只读）

在 Windows 的 **WSL Bash** 中执行以下完整命令。把 `ROUTER=...` 改成实际路由器 LAN IP，确认电脑有充足可用空间（全盘 64GB eMMC 的原始备份约为 64GB，压缩后大小取决于数据），最好在稳定有线连接下操作：

```bash
set -euo pipefail
ROUTER=192.168.6.1  # 仅举例，改为实际 IP
mkdir -p "$HOME/rax3000z-backup"
cd "$HOME/rax3000z-backup"
ssh -T "root@$ROUTER" 'dd if=/dev/mmcblk0boot0 bs=1M 2>/dev/null' > boot0.bin
ssh -T "root@$ROUTER" 'dd if=/dev/mmcblk0boot1 bs=1M 2>/dev/null' > boot1.bin
ssh -T "root@$ROUTER" 'dd if=/dev/mmcblk0 bs=4M 2>/dev/null' > emmc-userdata-full.img
sha256sum boot0.bin boot1.bin emmc-userdata-full.img > SHA256SUMS.txt
sha256sum -c SHA256SUMS.txt
ls -lh boot0.bin boot1.bin emmc-userdata-full.img SHA256SUMS.txt
```

注意：`dd if=` **只读取**路由器闪存，`>` 是写到 **WSL 电脑目录**，不会写回路由器。请勿在 Windows PowerShell 5.1 里直接用 `>` 接收二进制 SSH 流，避免字节编码/重定向问题。检查 `ssh` 退出码、备份长度及校验值，不能只看文件存在。该镜像可能包含**全部路由器个人配置和 Docker 数据**，妥善加密保管。若磁盘空间或网络条件不足，至少按实际 GPT 逐个备份 boot0、boot1、factory、fip、kernel、rootfs 和 GPT，具体命令须基于审计输出生成，而不是假定 `/dev/mmcblk0p3` 一定是 fip。

**全盘备份不是将来可以盲目 `dd of=/dev/mmcblk0` 恢复的授权**；恢复时还要核实设备、GPT、硬件 boot 分区和数据分区内容，不建议覆盖新写入的业务数据。

### 2.3 确认恢复通道是真正可用的

- 记下自定义 U-Boot 型号、版本与默认入口；目前设备能上网，**不必为了测试入口随意重启或按键**。
- 保存“现在正在正常使用”的**原第三方固件镜像**及其 SHA256。如果没有，就至少保存能回到当前状态的分区备份。
- 了解当前 U-Boot 页面究竟支持 `sysupgrade.bin`、legacy kernel `.bin`，还是 `.itb` FIT；不同版本无法通用，不能仅根据通用教程操作。
- 确认一台电脑可有线接入 LAN，知道固定 IP 的应急设置方法。有条件准备 UART/TTL 串口，但不要在不理解电压和接线的情况下尝试。

## 第 3 步：对自己编译的镜像做离线预检

GitHub Actions 成功后，从 `bin/targets/mediatek/mt7981` 取得自编译 `*sysupgrade.bin`。下载 audit 文件和镜像到电脑（Windows 可用 WSL/Python 运行）：

```bash
python3 scripts/firmware_preflight.py \
  --audit xr30-audit.txt \
  --image immortalwrt-mediatek-mt7981-cmcc_rax3000m-emmc-squashfs-sysupgrade.bin \
  --target cmcc,rax3000m-emmc
```

此检查读取 sysupgrade TAR 的 `kernel/root` 文件大小，与审计表里的 `kernel/rootfs` 分区容量比较；会保守留 1MiB 内核余量、8MiB rootfs 余量（经验安全阈值，不保证所有 overlay 机制都适用）；发现 `production` 活动槽、目标型号不一致或分区不足时直接 BLOCKED。它**不检查固件签名、U-Boot 可引导性或驱动**。如果使用原生目标，则先单独构建对应镜像，命令中使用 `--target cmcc,xr30-emmc`。

下一步在路由器**只做校验**（仍不刷入）：

```sh
sysupgrade -T /tmp/你的固件文件名-sysupgrade.bin
```

这条命令只是 `sysupgrade` 测试，不执行刷写。如果验证失败，记录错误并停止。**不要使用 `sysupgrade -F` 绕过机型检查**。即使 `-T` 通过，也仍需人工核查当前固件的升级脚本、活动启动槽和镜像格式，才能决定后续刷机方式。

## 第 4 步：恢复方案（按故障程度）

| 故障 | 恢复优先级 | 处理思路 |
|---|---|---|
| 新系统能启动，只是插件/网络配置异常 | 最高 | 首先通过 LAN/SSH/LuCI 修复配置；避免更改 U-Boot/GPT |
| 新系统无法启动，但原自定义 U-Boot 可正常进入 | 高 | 使用已经验证**可由该 U-Boot 接受**的旧系统恢复镜像；不要把 sysupgrade TAR 直接当作任意 Web-UI 固件 |
| U-Boot 支持并已配置双系统、另一个槽能启动 | 高 | 参考该 U-Boot 自身文档切回原正常槽位；**不要直接套用别人 `fw_setenv` 命令** |
| 系统与恢复页面都无法进入 | 专业操作 | 根据保留的 boot0/FIP/GPT 和原始镜像判断是否需 UART/硬件修复；不要试错覆盖引导区 |

**不提供任何自动执行的 GPT、BL2、FIP、`rootfs` 覆盖或 `fw_setenv` 脚本**，因为现在还缺少关键设备实况信息。恢复动作一旦写错设备节点，可能导致路由器完全失去启动能力。

## 相关公开源码与教程

- [Star-Song 作者项目](https://github.com/Star-Song/Actions-rax3000z-emmc)
- [hanwckf 21.02 的 `platform.sh`（选择 eMMC 升级）](https://github.com/hanwckf/immortalwrt-mt798x/blob/openwrt-21.02/target/linux/mediatek/mt7981/base-files/lib/upgrade/platform.sh)
- [hanwckf 的 `emmc.sh`（写 kernel/rootfs）](https://github.com/hanwckf/immortalwrt-mt798x/blob/openwrt-21.02/package/base-files/files/lib/upgrade/emmc.sh)
- [hanwckf 的 `mt7981.mk`（XR30 eMMC 与 RAX3000M eMMC 镜像元数据）](https://github.com/hanwckf/immortalwrt-mt798x/blob/openwrt-21.02/target/linux/mediatek/image/mt7981.mk)
- [lgs2007m 自定义 U-Boot / GPT / 双系统教程](https://github.com/lgs2007m/Actions-OpenWrt/blob/main/Tutorial/RAX3000M-eMMC_XR30-eMMC.md)
- [OpenWrt 官方备份及还原](https://openwrt.org/docs/guide-user/troubleshooting/backup_restore)
