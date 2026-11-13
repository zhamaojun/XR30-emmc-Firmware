"""Structural checks on the in-tree Lua LuCI package (no Lua interpreter needed)."""
import unittest

from lua_syntax import block_balance, bracket_balance, lua_files, strip_comments_and_strings


class LuaStructureTests(unittest.TestCase):
    def test_strip_removes_comments_and_strings(self):
        src = 'local a = "end end end" -- end\n--[[ end\nend ]] local b = 1\n'
        stripped = strip_comments_and_strings(src)
        self.assertNotIn('end', stripped.replace(' ', ''))
        # Line count must be preserved so offsets stay meaningful.
        self.assertEqual(src.count('\n'), stripped.count('\n'))

    def test_block_keywords_balance(self):
        self.assertEqual(block_balance('function f() end'), (1, 1))
        self.assertEqual(block_balance('if x then y() end'), (1, 1))
        # `do` here belongs to `for`, so exactly one block, not two.
        self.assertEqual(block_balance('for k, v in pairs(t) do x() end'), (1, 1))
        self.assertEqual(block_balance('while x do y() end'), (1, 1))
        self.assertEqual(block_balance('do x() end'), (1, 1))
        opens, closes = block_balance('function f() if a then while b do end end end')
        self.assertEqual(opens, closes)

    def test_bracket_balance(self):
        self.assertTrue(bracket_balance('f(a[b]{c})'))
        self.assertFalse(bracket_balance('f(a[b)}'))
        # Brackets living inside a string literal must be ignored.
        self.assertTrue(bracket_balance('f(") unbalanced quote content")'))

    def test_every_in_tree_lua_file_is_structurally_sound(self):
        files = lua_files()
        self.assertTrue(files, 'expected at least one .lua file in the in-tree package')
        for path in files:
            src = path.read_text(encoding='utf-8')
            with self.subTest(file=path.name):
                opens, closes = block_balance(src)
                self.assertEqual(
                    opens, closes,
                    f'{path.name}: {opens} block openers vs {closes} "end" tokens')
                self.assertTrue(
                    bracket_balance(src),
                    f'{path.name}: unbalanced (), [] or {{}}')

    def test_cbi_model_declares_a_map_and_returns_it(self):
        model = (lua_path('luasrc/model/cbi/tailscale/status.lua')).read_text(encoding='utf-8')
        self.assertIn('Map("tailscale"', model)
        self.assertTrue(model.rstrip().endswith('return m'),
                        'CBI models must return the Map object')

    def test_controller_registers_under_services(self):
        ctrl = (lua_path('luasrc/controller/tailscale.lua')).read_text(encoding='utf-8')
        self.assertIn('entry(', ctrl)
        self.assertIn('"admin", "services", "tailscale"', ctrl)
        self.assertIn('cbi("tailscale/status")', ctrl)


def lua_path(relative):
    from lua_syntax import LUA_ROOT
    return LUA_ROOT / relative


if __name__ == '__main__':
    unittest.main()
