#
# Conservative, reversible network tuning for the XR30 / MT7981.
#
# Scope is deliberately narrow and documented so nothing here can fight the
# hardware acceleration path. See files/etc/uci-defaults for the exact values.
#
include $(TOPDIR)/rules.mk

PKG_NAME:=xr30-network-tuning
PKG_VERSION:=1.0.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKG_MAINTAINER:=XR30-emmc-Firmware maintainers

include $(INCLUDE_DIR)/package.mk

define Package/$(PKG_NAME)
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Reversible network tuning for XR30 (buffers, backlog, local BBR)
  DEPENDS:=+kmod-tcp-bbr
  PKGARCH:=all
endef

define Package/$(PKG_NAME)/description
 Small, reversible tuning for MT7981: sysctl buffers/backlog/local BBR plus
 a boot-time cpufreq governor fix (schedutil). The kernel defaults to the
 userspace governor with no daemon, so without the boot script the CPUs sit
 at their minimum frequency and cap HNAT/proxy throughput.

 It does NOT touch flow-offload (must stay exclusive with MTK HNAT), does
 NOT change qdisc (SQM/CAKE is an operator runtime choice) and does NOT
 enable TCP Fast Open (not compiled into this 5.4 kernel).

 Revert: delete the marked block from /etc/sysctl.conf,
 /etc/init.d/xr30-cpufreq disable, reboot.
endef

define Build/Compile
endef

define Package/$(PKG_NAME)/install
	$(INSTALL_DIR) $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./files/etc/uci-defaults/99-xr30-network-tuning $(1)/etc/uci-defaults/99-xr30-network-tuning
	$(INSTALL_BIN) ./files/etc/uci-defaults/98-xr30-cpufreq-enable $(1)/etc/uci-defaults/98-xr30-cpufreq-enable
	$(INSTALL_DIR) $(1)/etc/init.d
	$(INSTALL_BIN) ./files/etc/init.d/xr30-cpufreq $(1)/etc/init.d/xr30-cpufreq
endef

$(eval $(call BuildPackage,$(PKG_NAME)))
