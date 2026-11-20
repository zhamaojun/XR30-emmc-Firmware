#
# Reversible network defaults for the XR30 / MT7981, tuned for "just works".
#
# See files/etc/uci-defaults for the exact values and their rationale. Every
# change is a documented uci/sysctl write that can be reverted by hand.
#
include $(TOPDIR)/rules.mk

PKG_NAME:=xr30-network-tuning
PKG_VERSION:=3.0.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKG_MAINTAINER:=XR30-emmc-Firmware maintainers

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Reversible network defaults for XR30 (offload, buffers, local BBR)
  DEPENDS:=+kmod-tcp-bbr +sqm-scripts +kmod-sched-cake +luci-app-turboacc-mtk
  PKGARCH:=all
endef

define Package/$(PKG_NAME)/description
 Reversible defaults for a wired gaming client on a ~120/80 Mbit WAN.

 Hardware offload stays ON for full line speed and minimal CPU, BBR is pinned
 for the router's own TCP (the userspace proxy's connections to its remote
 node - offloaded/forwarded flows never use the local TCP stack, so BBR cannot
 speed those up). Socket buffers are raised, swappiness is lowered so the eMMC
 is not used for paging, and UDP conntrack timeouts are lengthened so game and
 accelerator UDP flows are not rebuilt constantly.

 SQM is shipped CONFIGURED BUT DISABLED. Shaping below the real line rate is
 the only way to remove bufferbloat in the download direction - the queue that
 matters is in the modem/ISP, and the only way to take it over is to make the
 router the bottleneck. The owner chose full speed plus consciously avoiding
 bulk downloads instead. Enabling it later is one checkbox in LuCI; the
 interface, overhead and rates are already correct for this line.

 It does NOT touch flow-offload rules, does NOT enable TCP Fast Open (not
 compiled into this 5.4 kernel) and does NOT set net.core.default_qdisc,
 because sch_fq is not built here; the kernel default is already fq_codel
 via OpenWrt's 661-use_fq_codel_by_default.patch.

 To opt into shaping instead:
   LuCI -> Network -> SQM queue -> tick Enable, or
   uci set sqm.wan.enabled='1'; uci commit sqm; /etc/init.d/sqm restart
   uci set turboacc.config.fastpath='disabled'; uci commit turboacc
   /etc/init.d/turboacc restart
 (HNAT must be off or it shortcuts packets past the qdisc and CAKE becomes a
 no-op in the download direction.)

 To revert everything: delete the marked block from /etc/sysctl.conf, then
 remove /etc/uci-defaults/97-xr30-hardware-offload and 99-xr30-network-tuning
 and reboot.
endef

define Build/Compile
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./files/etc/uci-defaults/99-xr30-network-tuning $(1)/etc/uci-defaults/99-xr30-network-tuning
	$(INSTALL_BIN) ./files/etc/uci-defaults/97-xr30-hardware-offload $(1)/etc/uci-defaults/97-xr30-hardware-offload
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
