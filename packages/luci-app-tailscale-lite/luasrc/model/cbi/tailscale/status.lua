-- LuCI CBI model for luci-app-tailscale-lite (Lua, OpenWrt 21.02).
--
-- The upstream community packages are JS-view based and need LuCI 22.03+.
-- This model only uses the Lua CBI forms shipped with 21.02.
--
-- Read-only by default: it reports state and never starts a tunnel on its own.
-- The only writes are the on/off switch (procd enable/disable) and three
-- settings that feed/packages/net/tailscale's init script already understands.

local sys = require "luci.sys"
local fs = require "nixio.fs"
local jsonc = require "luci.jsonc"
local util = require "luci.util"

local TAILSCALED = "/usr/sbin/tailscaled"
local CLI = "/usr/sbin/tailscale"

local m, s, o

local function cli_available()
	return fs.access(CLI) ~= nil
end

local function is_running()
	if not fs.access(TAILSCALED) then
		return false
	end
	if sys.call("/etc/init.d/tailscale status >/dev/null 2>&1") == 0 then
		return true
	end
	-- Fall back to process presence for PID 1s without a status action.
	return sys.call("pgrep -x tailscaled >/dev/null 2>&1") == 0
end

local function backend_state()
	if not is_running() or not cli_available() then
		return nil
	end
	local raw = sys.exec(CLI .. " status --json 2>/dev/null")
	if not raw or #raw < 2 then
		return nil
	end
	local ok, parsed = pcall(jsonc.parse, raw)
	if not ok or type(parsed) ~= "table" then
		return nil
	end
	return parsed
end

local function state_text(st)
	if not is_running() then
		return translate("NOT RUNNING")
	end
	if not st then
		return translate("RUNNING (state unavailable)")
	end
	return translatef("RUNNING (%s)", tostring(st.BackendState or "unknown"))
end

m = Map("tailscale", translate("Tailscale"),
	translate("Tailscale is a zero-configuration WireGuard-based mesh VPN. " ..
		"This page is the Lua implementation for the Lua-based LuCI in " ..
		"OpenWrt 21.02; the upstream community packages require LuCI 22.03 " ..
		"or newer and will not render here."))

m.apply_on_parse = true

-- ---------------------------------------------------------------------------
-- Status (read-only)
-- ---------------------------------------------------------------------------
s = m:section(TypedSection, "settings", translate("Status"))
s.anonymous = true
s.addremove = false

o = s:option(DummyValue, "_service", translate("Service"))
o.cfgvalue = function()
	return state_text(nil)
end

o = s:option(DummyValue, "_hostname", translate("Device name"))
o.cfgvalue = function()
	local st = backend_state()
	if st and type(st.Self) == "table" then
		return tostring(st.Self.HostName or "-")
	end
	return "-"
end

o = s:option(DummyValue, "_ips", translate("Tailscale IPs"))
o.cfgvalue = function()
	local st = backend_state()
	if st and type(st.Self) == "table" and type(st.Self.TailscaleIPs) == "table" then
		return table.concat(st.Self.TailscaleIPs, ", ")
	end
	return "-"
end

o = s:option(DummyValue, "_login", translate("Login"))
o.rawhtml = true
o.cfgvalue = function()
	local st = backend_state()
	if not is_running() then
		return translate("Start the service to see login state.")
	end
	if not st then
		return translate("Login state unavailable.")
	end
	if st.BackendState == "NeedsLogin" and type(st.AuthURL) == "string" and #st.AuthURL > 0 then
		return '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
			% { util.pcdata(st.AuthURL), translate("Open the Tailscale login page") }
	end
	if st.BackendState == "Running" then
		return translate("Logged in.")
	end
	return translatef("State: %s", tostring(st.BackendState or "unknown"))
end

-- ---------------------------------------------------------------------------
-- Settings
-- ---------------------------------------------------------------------------
s = m:section(TypedSection, "settings", translate("Settings"))
s.anonymous = true
s.addremove = false

o = s:option(Flag, "enabled", translate("Enable"),
	translate("Start the daemon automatically at boot. This toggles the " ..
		"procd service state; it does not configure a tunnel."))
o.rmempty = false
o.default = "0"
o.cfgvalue = function(self, section)
	return (sys.call("/etc/init.d/tailscale enabled >/dev/null 2>&1") == 0) and "1" or "0"
end
o.write = function(self, section, value)
	-- Keep a uci record so the form counts as modified, then act on procd.
	self.map:set(section, self.option, value)
	if value == "1" then
		sys.call("/etc/init.d/tailscale enable >/dev/null 2>&1")
		sys.call("/etc/init.d/tailscale start >/dev/null 2>&1")
	else
		sys.call("/etc/init.d/tailscale stop >/dev/null 2>&1")
		sys.call("/etc/init.d/tailscale disable >/dev/null 2>&1")
	end
end

o = s:option(Value, "port", translate("Listen port"),
	translate("UDP port advertised to peers. Default 41641."))
o.datatype = "port"
o.default = "41641"
o.rmempty = false

o = s:option(Value, "state_file", translate("State file"),
	translate("Persistent daemon state. Keep it on the rootfs overlay."))
o.default = "/etc/tailscale/tailscaled.state"
o.rmempty = true

o = s:option(Flag, "log_stdout", translate("Log stdout"),
	translate("Write daemon stdout to syslog."))
o.default = "1"
o.rmempty = false

o = s:option(Flag, "log_stderr", translate("Log stderr"),
	translate("Write daemon stderr to syslog."))
o.default = "1"
o.rmempty = false

return m
