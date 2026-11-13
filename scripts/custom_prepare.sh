#!/usr/bin/env bash
set -euo pipefail
PROFILE="${1:?profile required}"
DEST="${2:?OpenWrt source directory required}"
[[ -d "$DEST" && -f "$DEST/feeds.conf.default" ]] || { echo 'invalid source path'; exit 1; }
case "$PROFILE" in baseline|performance|full) ;; *) echo "unsupported profile $PROFILE"; exit 1;; esac

# Repository root: this script lives in <repo>/scripts/.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -d "$REPO_ROOT/packages" ]] || { echo "ERROR: in-tree packages/ missing under $REPO_ROOT"; exit 1; }

# Pinned third-party revisions. Bumping these requires re-verifying the build,
# because a LuCI package written for 22.03+ will render as a blank page on the
# Lua-based LuCI in 21.02.
KENZOK8_SHA='8099fdd55809957fc4b02c5f910be1fc329ae6af'

# Copy this repository's in-tree LuCI packages (all profiles).
# packages/luci-app-tailscale-lite is a Lua/CBI page written for 21.02; the
# upstream community luci-app-tailscale is JS-view based and needs 22.03+.
copy_in_tree_packages() {
  local src="$1/packages"
  [[ -d "$src" ]] || return 0
  for pkg in "$src"/*/; do
    [[ -f "$pkg/Makefile" ]] || continue
    local name
    name="$(basename "$pkg")"
    rm -rf "$DEST/package/$name"
    cp -a "$pkg" "$DEST/package/"
    test -s "$DEST/package/$name/Makefile"
    echo "Copied in-tree package: $name"
  done
}

fetch_pinned_tarball() {
  local repo="$1" sha="$2" dest="$3"
  mkdir -p "$dest"
  curl -fsSL "https://codeload.github.com/${repo}/tar.gz/${sha}" \
    | tar -xz -C "$dest" --strip-components=1
}

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

  # AdGuard Home LuCI (kenzok8). This one really is Lua/CBI (menu uses
  # "type": "cbi"/"form"), and its README states 21.02 compatibility, so it
  # works with our Lua LuCI. Pinned to an explicit commit, not a branch head.
  tmp_agh="$(mktemp -d)"
  fetch_pinned_tarball kenzok8/openwrt-packages "$KENZOK8_SHA" "$tmp_agh/pkg"
  test -d "$tmp_agh/pkg/luci-app-adguardhome"
  test -s "$tmp_agh/pkg/luci-app-adguardhome/Makefile"
  # Must use the adguardhome binary we already compile, not a second one.
  grep -q 'PACKAGE_$(PKG_NAME)_INCLUDE_binary' "$tmp_agh/pkg/luci-app-adguardhome/Makefile" \
    || { echo 'ERROR: luci-app-adguardhome Makefile lost its INCLUDE_binary switch'; exit 1; }
  rm -rf "$DEST/package/luci-app-adguardhome"
  cp -a "$tmp_agh/pkg/luci-app-adguardhome" "$DEST/package/"
  echo "$KENZOK8_SHA" > "$DEST/kenzok8-source-sha.txt"
  rm -rf "$tmp_agh"
fi

# Always last, so in-tree packages win over any feed-provided namesake.
copy_in_tree_packages "$REPO_ROOT"
