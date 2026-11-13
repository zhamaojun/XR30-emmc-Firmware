-- LuCI controller for luci-app-tailscale-lite (Lua/CBI, OpenWrt 21.02).
module("luci.controller.tailscale", package.seeall)

function index()
	-- Fail closed: no menu when the tailscale CLI is absent.
	if not nixio.fs.access("/usr/sbin/tailscale") then
		return
	end
	entry({"admin", "services", "tailscale"}, cbi("tailscale/status"), _("Tailscale"), 60)
end
