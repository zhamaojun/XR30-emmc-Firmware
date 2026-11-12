请接管我当前工作区的 RAX3000Z 增强版（XR30 eMMC）定制 ImmortalWrt 项目，按“开发 → GitHub Actions 编译验证 → 镜像离线审计”的顺序持续完成，不要只给建议。首先阅读 AGENTS.md、README-DSH.md、docs/DSH_HANDOFF.md、docs/DSH_TASKS.md、README-CUSTOM.md 和当前构建脚本，再检查 Git 状态并在新的功能分支工作（不要直接修改 main）。

硬件已经验证：现在运行的是作者的 ImmortalWrt 21.02，board_name 为 cmcc,rax3000m-emmc；现有 GPT 分区 p4 kernel 32MiB、p5 rootfs 2GiB、p6 ext4 55.1GiB。保留 26MHz eMMC、XR30 白色 LED GPIO34、原机 EEPROM、现有 U-Boot 和全部分区，不要修改它们。初始源码先从 ab766cbcb0cc22a64e8bf816443bf3e1a56614bd 开始，核对并锁定可用的 feeds。

我要的功能：MTK HNAT、MTK eQoS、UPnP，OpenClash（包含可正常运行的内核与依赖）、SmartDNS（MosDNS 可作为后续替代）、WireGuard、Tailscale、Docker/Dockerman、AdGuard Home、SQM/CAKE（预装但默认关闭）和 iStore。分 baseline / performance / full 三档。明确解决旧 Linux 5.4 + iptables 源码、LuCI 包、Go 工具链与 iStore 的兼容性，不要仅把 Kconfig=y 当成安装成功。

请先跑本地 doctor 和单元测试，修复真实问题，然后尽量自主推进 GitHub Actions baseline；成功后按顺序做 performance 和 full。只有在已确认是我自己的 Fork、已登录 GitHub CLI、且获得提交/推送权限时才能将修改推送到该 Fork 的新分支并运行远端 Actions；否则保留本地成果，列出确切阻塞而不是猜测。所有编译失败都要读取真实日志、定位首次有效错误并针对修复；禁止原样循环重试，也不必因任意 30 分钟或固定工具调用次数而中止有效开发。

每阶段更新 docs/DSH_PROGRESS.md，记录代码提交、源码和 feeds SHA、CI 链接、构建结果、包清单、镜像哈希与 kernel/root 实际内容尺寸。最后给我推荐最稳定的配置档位和下一步待验证清单。

重要安全边界：当前任务只允许操作源码、工作区和经授权的 GitHub Actions。禁止主动 SSH 连接路由器、刷机、重启、格式化、修改 GPT/U-Boot/EEPROM、向 p4/p5/p6 写数据、使用 sysupgrade -F 或强制忽略镜像兼容性检查。固件编译成功也不能自行刷入。先开始工作，不需要每完成一个小任务就询问，但涉及真实路由器、权限提升、公开发布、密钥处理时必须停下请求明确许可。
