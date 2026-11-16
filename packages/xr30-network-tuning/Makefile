#
# Reversible game-latency and network tuning for the XR30 / MT7981.
#
# See files/etc/uci-defaults for the exact values and their rationale. Every
# change is a documented uci/sysctl write that can be reverted by hand.
#
include $(TOPDIR)/rules.mk

PKG_NAME:=xr30-network-tuning
PKG_VERSION:=2.0.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKG_MAINTAINER:=XR30-emmc-Firmware maintainers

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Reversible latency tuning for XR30 (CAKE, buffers, local BBR)
  DEPENDS:=+kmod-tcp-bbr +sqm-scripts +kmod-sched-cake +luci-app-turboacc-mtk
  PKGARCH:=all
endef

define Package/$(PKG_NAME)/description
 Tuning for a wired gaming client on a ~120/80 Mbit WAN.

 On first boot it enables SQM with CAKE (piece_of_cake.qos plus per-host
 fairness) and disables MTK HNAT, because HNAT bypasses the qdisc and would
 make CAKE ineffective. It also raises socket buffers, lowers swappiness so
 the eMMC is not used for paging, and lengthens UDP conntrack timeouts so
 game and accelerator UDP flows are not rebuilt constantly.

 It does NOT touch flow-offload rules, does NOT enable TCP Fast Open (not
 compiled into this 5.4 kernel) and does NOT set net.core.default_qdisc,
 because sch_fq is not built here; the kernel default is already fq_codel
 via OpenWrt's 661-use_fq_codel_by_default.patch.

 Revert: /etc/init.d/sqm stop; /etc/init.d/sqm disable;
         uci set turboacc.config.fastpath='mediatek_hnat'; uci commit turboacc;
         /etc/init.d/turboacc restart;
         delete the marked block from /etc/sysctl.conf; reboot.
endef

define Build/Compile
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./files/etc/uci-defaults/99-xr30-network-tuning $(1)/etc/uci-defaults/99-xr30-network-tuning
	$(INSTALL_BIN) ./files/etc/uci-defaults/97-xr30-game-latency $(1)/etc/uci-defaults/97-xr30-game-latency
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
