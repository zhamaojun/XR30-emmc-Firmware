#!/bin/sh
# RAX3000Z enhanced / XR30 eMMC. BACKUP, NOT RESTORE.
# The ONLY writes are to /tmp/xr30-critical-backup (volatile RAM), NEVER to /dev/mmc*.
# Intended ONLY for the exact 2026-11-13 audited layout:
# board cmcc,rax3000m-emmc, p1 bootenv 512KiB, p2 factory 2MiB,
# p3 fip 2MiB, p4 kernel 32MiB, p5 rootfs 2GiB.
set -eu
umask 077
DIR=/tmp/xr30-critical-backup
BOARD=$(cat /tmp/sysinfo/board_name 2>/dev/null || echo UNKNOWN)
[ "$BOARD" = 'cmcc,rax3000m-emmc' ] || { echo "STOP: unknown board: $BOARD" >&2; exit 1; }
[ -b /dev/mmcblk0 ] || { echo 'STOP: eMMC block device missing' >&2; exit 1; }
for item in '1 1024 u-boot-env' '2 4096 factory' '3 4096 fip' '4 65536 kernel' '5 4096000 rootfs'; do
  set -- $item
  part="$1" expect="$2" label="$3"
  actual=$(cat "/sys/class/block/mmcblk0p${part}/size" 2>/dev/null || echo UNKNOWN)
  [ "$actual" = "$expect" ] || { echo "STOP: p${part} is ${actual} sectors, expected ${expect}" >&2; exit 1; }
  blkid "/dev/mmcblk0p${part}" 2>/dev/null | grep -Fq "PARTLABEL=\"$label\"" || {
    echo "STOP: unexpected/missing p${part} PARTLABEL $label" >&2; exit 1;
  }
done
for b in mmcblk0boot0 mmcblk0boot1; do
  [ -b "/dev/$b" ] || { echo "STOP: /dev/$b missing" >&2; exit 1; }
  bsize=$(cat "/sys/class/block/$b/size" 2>/dev/null || echo UNKNOWN)
  case "$bsize" in ''|*[!0-9]*) echo "STOP: invalid $b size" >&2; exit 1;; esac
  [ "$bsize" -gt 0 ] && [ "$bsize" -le 32768 ] || { echo "STOP: unusual $b size" >&2; exit 1; }
done
SECTORS=$(cat /sys/class/block/mmcblk0/size)
case "$SECTORS" in ''|*[!0-9]*) echo 'STOP: invalid disk size' >&2; exit 1;; esac
[ "$SECTORS" -ge 119781409 ] || { echo 'STOP: unexpected disk size' >&2; exit 1; }
B0=$(cat /sys/class/block/mmcblk0boot0/size)
B1=$(cat /sys/class/block/mmcblk0boot1/size)
REQUIRED_KB=$(((B0 + B1 + 1024 + 4096 + 4096 + 65536 + 34 + 33) / 2 + 12288))
FREE_KB=$(df -k /tmp | awk 'NR==2 {print $4}')
case "$FREE_KB" in ''|*[!0-9]*) echo 'STOP: cannot assess free /tmp RAM; back up manually' >&2; exit 1;; esac
[ "$FREE_KB" -ge "$REQUIRED_KB" ] || { echo "STOP: /tmp has ${FREE_KB}KB free, need ${REQUIRED_KB}KB" >&2; exit 1; }
mkdir -p "$DIR"
[ ! -e "$DIR/BACKUP_COMPLETE" ] || { echo 'STOP: an earlier backup already exists, move it to PC first' >&2; exit 1; }
echo 'Backing up read-only boot/factory/kernel and GPT areas to volatile /tmp ...'
dd if=/dev/mmcblk0boot0 of="$DIR/emmc-boot0.bin" bs=1M
dd if=/dev/mmcblk0boot1 of="$DIR/emmc-boot1.bin" bs=1M
dd if=/dev/mmcblk0p1 of="$DIR/p1-uboot-env.bin" bs=1M
dd if=/dev/mmcblk0p2 of="$DIR/p2-factory.bin" bs=1M
dd if=/dev/mmcblk0p3 of="$DIR/p3-fip.bin" bs=1M
dd if=/dev/mmcblk0p4 of="$DIR/p4-kernel.bin" bs=1M
dd if=/dev/mmcblk0 of="$DIR/gpt-primary-first34sectors.bin" bs=512 count=34
dd if=/dev/mmcblk0 of="$DIR/gpt-secondary-last33sectors.bin" bs=512 skip=$((SECTORS - 33)) count=33
cat /proc/cmdline > "$DIR/kernel-cmdline.txt"
cat /etc/openwrt_release > "$DIR/openwrt-release.txt"
fdisk -l /dev/mmcblk0 > "$DIR/partition-layout.txt" 2>&1
blkid > "$DIR/blkid.txt" 2>&1
if command -v sysupgrade >/dev/null 2>&1; then
  sysupgrade -b "$DIR/config-backup.tar.gz" || { echo 'WARNING: configuration backup failed' >&2; exit 1; }
fi
if command -v opkg >/dev/null 2>&1; then opkg list-installed > "$DIR/installed-packages.txt"; fi
(cd "$DIR" && sha256sum *.bin config-backup.tar.gz 2>/dev/null > SHA256SUMS.txt)
echo "Created on $(date -u)" > "$DIR/BACKUP_COMPLETE"
ls -lh "$DIR"
echo "BACKUP COMPLETE: download $DIR to your PC immediately; /tmp is erased by reboot."
echo 'Do not publicly share these files: they include unique factory calibration and private configuration.'
echo 'Not backed up: p5 rootfs (live F2FS overlay), p6 ext4 55GiB data; see documentation.'
