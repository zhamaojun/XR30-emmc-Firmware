#!/bin/sh
# RAX3000Z / XR30 eMMC: READ-ONLY inspection. No flash, format, env write, or repartition.
# Run as root over SSH, redirect stdout to a file on your own computer.
set -u
printf '%s\n' 'XR30_AUDIT_VERSION|1' 'XR30_READONLY|YES'
if command -v board_name >/dev/null 2>&1; then
  printf 'XR30_BOARD|%s\n' "$(board_name 2>/dev/null)"
elif [ -r /tmp/sysinfo/board_name ]; then
  printf 'XR30_BOARD|%s\n' "$(cat /tmp/sysinfo/board_name)"
else
  printf '%s\n' 'XR30_BOARD|UNKNOWN'
fi
if [ -r /proc/device-tree/model ]; then
  model=$(tr -d '\000' </proc/device-tree/model)
  printf 'XR30_MODEL|%s\n' "$model"
fi
if [ -r /proc/cmdline ]; then
  printf 'XR30_BOOTARGS|%s\n' "$(cat /proc/cmdline)"
fi
if [ -r /etc/openwrt_release ]; then
  . /etc/openwrt_release
  printf 'XR30_DISTRO|%s|%s\n' "${DISTRIB_ID:-unknown}" "${DISTRIB_RELEASE:-unknown}"
fi
printf '%s\n' 'XR30_PARTITIONS_BEGIN'
for path in /sys/class/block/mmcblk0p*; do
  [ -d "$path" ] || continue
  dev=${path##*/}
  name=$(sed -n 's/^PARTNAME=//p' "$path/uevent" 2>/dev/null | head -n 1)
  if [ -z "$name" ] && command -v blkid >/dev/null 2>&1; then
    name=$(blkid -o value -s PARTLABEL "/dev/$dev" 2>/dev/null | head -n 1)
  fi
  sectors=$(cat "$path/size" 2>/dev/null || echo 0)
  case "$sectors" in ''|*[!0-9]*) sectors=0;; esac
  bytes=$((sectors * 512))
  printf 'XR30_PART|%s|%s|%s\n' "$name" "$dev" "$bytes"
done
printf '%s\n' 'XR30_PARTITIONS_END'
printf '%s\n' 'XR30_MMC_DEVICES_BEGIN'
for path in /sys/class/block/mmcblk0 /sys/class/block/mmcblk0boot0 /sys/class/block/mmcblk0boot1; do
  [ -d "$path" ] || continue
  dev=${path##*/}
  sectors=$(cat "$path/size" 2>/dev/null || echo 0)
  case "$sectors" in ''|*[!0-9]*) sectors=0;; esac
  printf 'XR30_MMC|%s|%s\n' "$dev" "$((sectors * 512))"
done
printf '%s\n' 'XR30_MMC_DEVICES_END'
if command -v fw_printenv >/dev/null 2>&1; then
  for key in dual_boot.current_slot bootconf bootcount boot_part; do
    line=$(fw_printenv "$key" 2>/dev/null | head -n 1)
    case "$line" in "$key="*)
       printf 'XR30_BOOTENV|%s|%s\n' "$key" "${line#*=}";;
    esac
  done
fi
if [ -r /proc/mounts ]; then
  awk '($2=="/" || $2=="/overlay" || $2=="/opt" || $2=="/mnt/data") {print "XR30_MOUNT|"$1"|"$2"|"$3}' /proc/mounts
fi
if command -v sysupgrade >/dev/null 2>&1; then
  printf '%s\n' 'XR30_SYSUPGRADE|FOUND'
else
  printf '%s\n' 'XR30_SYSUPGRADE|MISSING'
fi
printf '%s\n' 'XR30_AUDIT_COMPLETE|YES'
