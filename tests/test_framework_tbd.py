import unittest

from tools.apple_sdk_gen.generators.tbd import generate_tbd
from tools.apple_sdk_gen.models.symbol import Symbol
from tools.apple_sdk_gen.models.types import SymbolKind


class FrameworkTBDTest(unittest.TestCase):
    def test_exports_data_constants_but_not_enum_cases(self):
        symbols = [
            Symbol("tag-class", "kUTTagClassMIMEType", SymbolKind.VAR, usr="c:@kUTTagClassMIMEType"),
            Symbol("launch-defaults", "kLSLaunchDefaults", SymbolKind.ENUM_CASE,
                   usr="c:@E@LSLaunchFlags@kLSLaunchDefaults"),
        ]
        stub = generate_tbd("CoreServices", symbols, ["arm64-macos"])

        self.assertIn("_kUTTagClassMIMEType", stub)
        self.assertNotIn("_kLSLaunchDefaults", stub)

    def test_core_graphics_inline_constructors_are_not_exports(self):
        symbols = [
            Symbol(name, name, SymbolKind.FUNC, usr=f"c:@F@{name}")
            for name in ("CGRectMake", "CGRectApplyAffineTransform")
        ]
        stub = generate_tbd("CoreGraphics", symbols, ["arm64-macos"])
        self.assertNotIn("_CGRectMake", stub)
        self.assertIn("_CGRectApplyAffineTransform", stub)
