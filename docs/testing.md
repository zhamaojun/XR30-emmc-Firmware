# RAX3000Z XR30 eMMC 固件验证与性能测试

## 上机前必须核对

- 确认设备真的是 **RAX3000Z 增强版 / XR30 / eMMC**，不是 XR30 NAND 或 RAX3000M NAND。
- 设备目前使用的 U-Boot、eMMC 分区布局和现有系统；镜像的 sysupgrade 目标布局必须完全匹配。
- 备份设备出厂数据、eMMC 分区表、校准信息及可恢复通道。禁止拿他人的 EEPROM 覆盖原机。
- 首次构建仅供检查，不要直接刷机；有条件优先从恢复环境测试。
- 不附带刷入 GPT / BL2 / FIP 的 `dd` 命令，确认布局之前不得执行危险刷机操作。

## GitHub Actions 验证顺序

1. `baseline` ：验证 hanwckf 当前分支、XR30 LED GPIO 补丁、26 MHz eMMC 镜像生成。
2. `performance` ：在 baseline 成功基础上，增加 OpenClash、SmartDNS、WireGuard、Docker，检测依赖。
3. `full` ：再加入 iStore、AdGuard Home、Tailscale、SQM（仅安装，不默认启用）。
4. 每一步保存 `selected-config.txt`、`upstream-source-sha.txt`、CI 日志。把成功构建的各 feed SHA 和 OpenClash SHA 固定后再重复构建。
5. 如果发生编译失败，定位**第一条真正的编译错误**，不进行无意义整套重试。

## 上机后检查（在备份完成、确认可恢复后）

- 设备能启动、LAN/WAN 地址和 LAN DHCP 正确，投影白灯与红灯时序正确。
- Wi-Fi 2.4GHz/5GHz 能开启，MAC、发射地区参数正确，无异常温度和内核错误。
- 查看 HNAT 状态、CPU 负载、直连 WAN↔LAN 性能；不要用单个 Speedtest 断言硬件 NAT 是否生效。
- 测 OpenClash 关闭/开启下直连与代理性能，确认直连仍能有效使用硬件转发路径。
- 分别验证 DNS：53 端口仅由一个对客户端提供服务；检查 DHCP DNS 和本机解析、防泄漏、防回环。
- 组网：WireGuard / Tailscale 分别验证远程访问、MTU、子网路由及 LAN 可见性；不要同时强制接管默认路由。
- Docker：把数据放到正确挂载的 eMMC 数据分区，先不自动初始化或格式化 `/dev/mmcblk0p7`。
- QoS：先采集基础吞吐和满载延迟，随后只启用 MTK eQoS 或 SQM/CAKE 中一套方案，对比延迟/吞吐/CPU。
- IPv4 NAT：先确认公网/CGNAT 情况和上游 NAT 层数；UPnP 的外网映射不等于自动获得公网 IPv4。

## 建议测试表

| 场景 | 测量 | 判断 |
|---|---|---|
| 直连，HNAT on | LAN↔WAN 有线吞吐、CPU、丢包 | 与原版同条件对比 |
| OpenClash on | 代理吞吐、CPU、DNS 和直连流量 | 切换配置后无 DNS 泄漏/回环 |
| 满载上传下载 | `flent rrul`/Waveform bufferbloat、游戏 RTT | SQM 的收益是否抵消吞吐损失 |
| WireGuard | 双向带宽、持续 RTT | 稳定性与 MTU |
| eMMC | `dmesg` I/O/CRC 错误 | 26MHz 稳定优先 |

**注意：** 高功率版 EEPROM 和 52MHz 加速均未列入本方案，不改变射频校准数据/区域限制。
