#!/usr/bin/env bash
set -euo pipefail
PROFILE="${1:?profile required}"
DEST="${2:?OpenWrt source directory required}"
[[ -d "$DEST" && -f "$DEST/feeds.conf.default" ]] || { echo 'invalid source path'; exit 1; }
case "$PROFILE" in baseline|performance|full) ;; *) echo "unsupported profile $PROFILE"; exit 1;; esac

if [[ "$PROFILE" != baseline ]]; then
  # Official OpenClash package source, separate from the Mihomo runtime core.
  # HEAD is intentionally not called a known-good revision: pin after verification.
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  git clone --depth 1 --filter=blob:none --sparse \
    https://github.com/vernesong/OpenClash.git "$tmp_dir/OpenClash"
  git -C "$tmp_dir/OpenClash" sparse-checkout set luci-app-openclash
  test -s "$tmp_dir/OpenClash/luci-app-openclash/Makefile"
  test ! -e "$DEST/package/luci-app-openclash" || { echo 'Duplicate OpenClash package'; exit 1; }
  cp -a "$tmp_dir/OpenClash/luci-app-openclash" "$DEST/package/"
  git -C "$tmp_dir/OpenClash" rev-parse HEAD > "$DEST/openclash-source-sha.txt"
fi

if [[ "$PROFILE" = full ]]; then
  # iStore docs prescribe this feed; no runtime installation on the user's router.
  if ! grep -q '^src-git istore ' "$DEST/feeds.conf.default"; then
    echo 'src-git istore https://github.com/linkease/istore;main' >> "$DEST/feeds.conf.default"
  fi
fi
