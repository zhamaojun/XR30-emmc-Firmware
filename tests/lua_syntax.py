"""Structural Lua checks for in-tree LuCI files.

There is no Lua interpreter on the Windows build host and OpenWrt's luci.mk
only copies .lua files into the image, so a syntax error would first appear at
runtime as a blank LuCI page. This module does a conservative structural pass
(block keywords, brackets, string termination) so failures show up here.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
LUA_ROOT = ROOT / 'packages' / 'luci-app-tailscale-lite'

# Keywords that open a block requiring `end`, except `do` which also belongs to
# `for ... do` / `while ... do` and must not be counted twice.
_BLOCK_KW = re.compile(r'\b(function|if|for|while|do|end)\b')


def strip_comments_and_strings(src):
    """Remove Lua comments and string literals, preserving line count."""
    out = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        # Long bracket comment / string: --[[ ... ]] or [[ ... ]]
        if src.startswith('--[[', i):
            end = src.find(']]', i + 4)
            end = n if end < 0 else end + 2
            out.append(re.sub(r'[^\n]', ' ', src[i:end]))
            i = end
            continue
        if src.startswith('--', i):
            end = src.find('\n', i)
            end = n if end < 0 else end
            out.append(' ' * (end - i))
            i = end
            continue
        if ch in '"\'':
            quote = ch
            end = i + 1
            while end < n:
                if src[end] == '\\':
                    end += 2
                    continue
                if src[end] == quote:
                    end += 1
                    break
                end += 1
            out.append('""')
            i = end
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def block_balance(src):
    """Return (opens, closes) for Lua block keywords."""
    code = strip_comments_and_strings(src)
    opens = closes = 0
    pending_loop = 0
    for token in _BLOCK_KW.findall(code):
        if token in ('function', 'if'):
            opens += 1
        elif token in ('for', 'while'):
            opens += 1
            pending_loop += 1
        elif token == 'do':
            if pending_loop > 0:
                pending_loop -= 1   # this `do` belongs to for/while
            else:
                opens += 1          # standalone do ... end
        elif token == 'end':
            closes += 1
    return opens, closes


def bracket_balance(src):
    code = strip_comments_and_strings(src)
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack = []
    for ch in code:
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack.pop() != ch:
                return False
    return not stack


def lua_files():
    return sorted(LUA_ROOT.rglob('*.lua')) if LUA_ROOT.is_dir() else []
