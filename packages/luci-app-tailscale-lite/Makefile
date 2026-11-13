#
# LuCI support for Tailscale — Lua/CBI implementation for OpenWrt 21.02.
#
# The official and community luci-app-tailscale packages are all JS-view based
# (htdocs/luci-static/resources/view/*.js, 'require view' + view.extend) and
# therefore require LuCI 22.03+ client-side rendering. This package provides a
# minimal Lua/CBI equivalent that works on the Lua-based LuCI shipped with
# ImmortalWrt 21.02, which is what this firmware targets.
#
# Scope is deliberately small: service state, login state, enable/disable,
# port/working directory, and the login URL. It does not reimplement the
# Tailscale CLI, and it never writes to the router by itself.
#
include $(TOPDIR)/rules.mk

PKG_NAME:=luci-app-tailscale-lite
PKG_VERSION:=1.0.0
PKG_RELEASE:=1
PKG_LICENSE:=Apache-2.0
PKG_MAINTAINER:=XR30-emmc-Firmware maintainers

LUCI_TITLE:=LuCI support for Tailscale (Lua, 21.02 compatible)
LUCI_DESCRIPTION:=Minimal Lua/CBI Tailscale status and control page for \
 the Lua-based LuCI in OpenWrt 21.02. The community packages require 22.03+.
LUCI_DEPENDS:=+tailscale
LUCI_PKGARCH:=all

include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot signature
$(eval $(call BuildPackage,$(PKG_NAME)))
