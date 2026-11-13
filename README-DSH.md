# RAX3000Z XR30 eMMC — DeepSeek Harness 项目接入

此包历史来源为 **Star-Song/Actions-rax3000z-emmc**（已停更）的文件叠加包；**本仓库自 2026-11-13 起独立维护**，新接入直接 clone 本仓库即可，无需再 fork 作者仓库。本包不是完整源码仓库，也不是可刷写固件。结合已完成的 V3 Overlay 与 DeepSeek Harness 交接说明。

## Windows 10：推荐安装流程

1. ~~先到 <https://github.com/Star-Song/Actions-rax3000z-emmc/fork> Fork 到自己的 GitHub 账号~~（历史步骤；作者仓库已停更，本项目独立维护后直接 clone 本仓库即可）。
2. 安装 [Git for Windows](https://git-scm.com/downloads/win) 和 Node.js 官方当前稳定版本（建议 24.9+）。如只有 GitHub 网页，也可以先手动上传 ZIP 的文件到你的 Fork。
3. 解压本 ZIP 到一个**临时**文件夹，例如 `D:\XR30-DSH-Kit`。打开 Windows PowerShell：

   ```powershell
   Set-Location 'D:\XR30-DSH-Kit'
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_dsh_workspace.ps1 -ForkUrl 'https://github.com/你的用户名/Actions-rax3000z-emmc.git' -TargetPath 'D:\XR30-Firmware'
   ```

   这个脚本仅克隆用户自己的 Fork 并合并本 ZIP 文件；存在不同内容的文件会**停止而不覆盖**。如果你已经在电脑上 clone 了自己的 Fork，可只传 `-TargetPath`，省略 `-ForkUrl`。
4. 切换到项目目录，先完成本地静态检查（不编译固件、不操作路由器）：

   ```powershell
   Set-Location 'D:\XR30-Firmware'
   python .\scripts\dsh_project_doctor.py
   python -m unittest discover -s tests -v
   ```

5. 启动官方 DeepSeek Harness：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_dsh.ps1
   ```

   上述脚本使用官方文档的 `npx @deepseek-ai/dsh web`，默认网页地址 `http://127.0.0.1:3080`。首次运行下载 npm 依赖，需要联网。DSH 仍在开发预览期，首次成功运行后建议记录并固定已验证的 npm 版本，避免未来自动变化。如果你已经装了官方 DSH 桌面版，也可以直接在 Desktop 中选择该工作区，不需要脚本。
6. 在 DSH Web UI → **Settings → Models** 中填写自己的 DeepSeek API Key（不要放在仓库文件里）。在 **Choose workspace** 中选 `D:\XR30-Firmware`。权限建议 **workspace-write / ask**，不要切换 `danger-full-access`。复制 `docs/DSH_START_PROMPT.md` 发给 DSH 开始开发。

## 开发分支与 GitHub Actions

- 建议让 DSH 在 `feat/dsh-xr30-custom-firmware` 功能分支修改，而不是直接改 main。
- 当 DSH 实际完成静态验证、已确认 repo 是自己的 Fork 时，用户允许其继续通过 GitHub Actions 跑 `baseline → performance → full`。本包提供 `scripts/run_ci_profile.ps1`，需 **GitHub CLI** `gh` 已登录，并在远端仓库能找到 `build-xr30-custom.yml`；部署 CI 前应先提交、推送**用户授权的功能分支**。
- 若 Windows 本机缺 Python/Node/Git/gh、网络访问失败或 Actions 限制，请记录阻塞，不能声称已经编译成功。可用 GitHub 网页 Actions 启动。
- `docs/DSH_PROGRESS.md` 是交接与失败记录。不同 Agent 均需记录可复现证据。
- 编译成功不等于固件可刷！禁止 DSH 通过 SSH 连接设备、上传镜像、修改分区或执行任何刷机命令。刷机需要另外经用户确认。

## 已验证的设备与关键目标

- `cmcc,rax3000m-emmc`; 512MiB RAM; root by `PARTLABEL=rootfs`.
- GPT: p1 U-Boot env 512KiB, p2 factory 2MiB, p3 FIP 2MiB, p4 kernel 32MiB, p5 rootfs 2GiB, p6 ext4 55.1GiB.
- XR30 white LED GPIO 34; 26MHz eMMC; no NX30 Pro EEPROM; no partition changes.
- Source pin candidate `ab766cbcb0cc22a64e8bf816443bf3e1a56614bd`; pinned source != pinned package feeds.
- 3 profiles in workflow; `full` is higher compatibility risk because old OpenWrt 21.02 iptables + Linux 5.4.

## Agent 参考文档

- `AGENTS.md` — 目标、技术约束、安全边界。
- `docs/DSH_HANDOFF.md` — 任务详情、兼容性风险与验收条件。
- `docs/DSH_TASKS.md` — 分阶段清单。
- `docs/DSH_START_PROMPT.md` — 直接复制到 DSH 的中文任务。
- `docs/DSH_PROGRESS.md` — 真实执行结果、错误和恢复检查点。
- `README-CUSTOM.md`, `docs/verified-device-layout.md`, `docs/flash-safety-and-recovery.md` — V3 历史项目基线。

## 官方依据

- <https://github.com/deepseek-ai/deepseek-harness>
- <https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart>
- <https://deepseek-harness.github.io/deepseek-harness/en/reference/subsystems/permission-presets>

**状态声明：这是经过本地静态与单元检查的交接工程，不代表已在用户的 Windows 电脑部署 DSH、完成 GitHub Actions 编译或通过真实路由器测试。**
