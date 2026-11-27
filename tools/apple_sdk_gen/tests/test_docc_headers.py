import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.apple_sdk_gen.assembler.sdk_layout import assemble_sdk
from tools.apple_sdk_gen.crawler.framework import crawl_framework_symbols
from tools.apple_sdk_gen.crawler.symbol import parse_symbol
from tools.apple_sdk_gen.crawler.technologies import FrameworkInfo


CLANG = os.environ.get("CLANG") or shutil.which("clang")


def declaration(text, *platforms):
    return {"languages": ["occ"], "platforms": platforms,
            "tokens": [{"kind": "text", "text": text}]}


def page(title, kind, *declarations):
    return {
        "metadata": {"title": title, "role": "symbol", "symbolKind": kind},
        "primaryContentSections": [{"kind": "declarations", "declarations": declarations}],
    }


class DocC:
    def __init__(self, pages):
        self.pages = pages

    async def fetch_doc(self, path):
        return self.pages[path]

    async def symbols(self):
        return [await parse_symbol(self, path, "Foundation") for path in self.pages]


def assemble_header(directory, platform, symbols):
    sdk = assemble_sdk(directory, platform, "26.0", {"Foundation": symbols})
    return sdk / "System/Library/Frameworks/Foundation.framework/Headers/Foundation.h"


def address_pages(initializer):
    address = "/documentation/foundation/address"
    field_refs = {"number": {"title": "number", "url": f"{address}/number"},
                  "code": {"title": "code", "url": f"{address}/code"},
                  "initializer": {"title": initializer, "url": f"{address}/initializer"}}
    return {
        address: {
            **page("Address", "struct", declaration("typedef struct Address { ... } Address;")),
            "topicSections": [{"identifiers": ["number", "code", "initializer"]}],
            "references": {
                name: {"kind": "symbol", "role": "symbol", **ref}
                for name, ref in field_refs.items()
            },
        },
        f"{address}/number": page("number", "property", declaration("unsigned number;")),
        f"{address}/code": page("code", "property", declaration("unsigned char code;")),
    }


class DocCHeadersTest(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_objc_interface_omits_related_top_level_declarations(self):
        path = "/documentation/foundation/application"
        member = f"{path}/run"
        protocol = "/documentation/foundation/applicationdelegate"
        variable = "/documentation/foundation/sharedapplication"
        docc = DocC({
            path: {
                **page("Application", "class", declaration("@interface Application")),
                "topicSections": [{"identifiers": ["delegate", "variable", "run"]}],
                "references": {
                    name: {"kind": "symbol", "role": "symbol", "url": url}
                    for name, url in (("delegate", protocol), ("variable", variable), ("run", member))
                },
            },
            member: page("run", "method", declaration("- (void)run;")),
            protocol: page("ApplicationDelegate", "protocol", declaration("@protocol ApplicationDelegate")),
            variable: page("SharedApplication", "var", declaration("extern Application *SharedApplication;")),
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            contents = header.read_text()
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding",
                 "-fsyntax-only", "-Werror", "-isysroot", str(header.parents[5]),
                 "-include", str(header), "-x", "objective-c", "-"],
                input="void start(void) { [SharedApplication run]; }\n",
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(contents.count("extern Application *SharedApplication;"), 1)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_objc_classes_define_superclasses_before_subclasses(self):
        classes = {
            "Child": "@interface Child<ObjectType> : Parent<ObjectType>",
            "Peer": "@interface Peer",
            "Parent": "@interface Parent<ObjectType> : Root",
            "Root": "@interface Root",
        }
        docc = DocC({
            f"/documentation/foundation/{name.lower()}":
                page(name, "class", declaration(heading))
            for name, heading in classes.items()
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding",
                 "-fsyntax-only", "-Werror", "-isysroot", str(header.parents[5]),
                 "-include", str(header), "-x", "objective-c", "-"],
                input="Child<Root *> *child;\n", text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_coregraphics_callbacks_and_bitmap_constants_compile_as_objcxx(self):
        path = "/documentation/coregraphics"
        cases = ("kCGBitmapByteOrder32Little", "kCGBitmapAlphaInfoMask")
        pages = {
            f"{path}/cgbitmapinfo": {
                **page("CGBitmapInfo", "enum", declaration("enum CGBitmapInfo : uint32_t;")),
                "topicSections": [{"identifiers": list(cases)}],
                "references": {
                    name: {"kind": "symbol", "role": "symbol", "url": f"{path}/{name}"}
                    for name in cases
                },
            },
            **{f"{path}/{name}": page(name, "case", declaration(name)) for name in cases},
            f"{path}/callback": page("CGDone", "typealias", {
                "languages": ["occ"],
                "tokens": [
                    {"kind": "keyword", "text": "typedef"},
                    {"kind": "text", "text": " "},
                    {"kind": "typeIdentifier", "text": "void (*)(void *, _Bool)"},
                    {"kind": "text", "text": " CGDone;"},
                ],
            }),
            f"{path}/cgfontindex": page(
                "CGFontIndex", "typealias", declaration("typedef uint16_t CGFontIndex;"),
            ),
            f"{path}/cgdraw": page("CGDraw", "func", declaration("extern int CGDraw(void);")),
            f"{path}/fontindexmax": {
                **page("kCGFontIndexMax", "var", declaration("static const CGFontIndex kCGFontIndexMax;")),
                "metadata": {"title": "kCGFontIndexMax", "role": "symbol", "symbolKind": "var",
                             "externalID": "c:@kCGFontIndexMax"},
            },
            f"{path}/byteorder32host": page(
                "kCGBitmapByteOrder32Host", "var",
                declaration("static const CGBitmapInfo kCGBitmapByteOrder32Host;"),
            ),
        }
        docc = DocC(pages)
        symbols = [await parse_symbol(docc, name, "CoreGraphics") for name in pages]
        with tempfile.TemporaryDirectory() as directory:
            sdk = assemble_sdk(Path(directory), "macos", "26.5", {"CoreGraphics": symbols})
            framework = sdk / "System/Library/Frameworks/CoreGraphics.framework"
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos14.0", "-ffreestanding", "-fsyntax-only",
                 "-Werror", "-isysroot", str(sdk), "-x", "objective-c++", "-std=c++20", "-"],
                input=("#import <CoreGraphics/CoreGraphics.h>\n"
                       "extern \"C\" int CGDraw(void);\n"
                       "static_assert(__is_same(CGDone, void (*)(void *, bool)));\n"
                       "constexpr CGBitmapInfo image = kCGBitmapByteOrder32Host | kCGBitmapAlphaInfoMask;\n"
                       "static_assert(image == 0x201f && kCGFontIndexMax == 65534);\n"),
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("_kCGFontIndexMax", (framework / "CoreGraphics.tbd").read_text())

    async def test_appkit_event_and_activation_values(self):
        enums = {
            "NSEventType": {"NSEventTypeApplicationDefined": 15, "NSEventTypeLeftMouseDown": 1},
            "NSEventSubtype": {"NSEventSubtypeApplicationActivated": 1},
            "NSApplicationActivationPolicy": {
                "NSApplicationActivationPolicyAccessory": 1,
                "NSApplicationActivationPolicyProhibited": 2,
                "NSApplicationActivationPolicyRegular": 0,
            },
        }
        pages = {}
        for name, cases in enums.items():
            path = f"/documentation/appkit/{name.lower()}"
            pages[path] = {
                **page(name, "enum", declaration(f"enum {name} : NSInteger", "macOS")),
                "topicSections": [{"identifiers": list(cases)}],
                "references": {
                    case: {"kind": "symbol", "role": "symbol", "url": f"{path}/{case.lower()}"}
                    for case in cases
                },
            }
            for case in cases:
                pages[f"{path}/{case.lower()}"] = {"metadata": {
                    "title": case, "role": "symbol", "symbolKind": "case",
                    "externalID": f"c:@E@{name}@{case}",
                }}
        docc = DocC(pages)
        symbols = [await parse_symbol(docc, path, "AppKit") for path in pages]
        with tempfile.TemporaryDirectory() as directory:
            sdk = assemble_sdk(Path(directory), "macos", "26.5", {"AppKit": symbols})
            header = (sdk / "System/Library/Frameworks/AppKit.framework/Headers/AppKit.h").read_text()
        self.assertIn("NSEventTypeApplicationDefined = 15,", header)
        self.assertIn("NSEventSubtypeApplicationActivated = 1,", header)
        self.assertIn("NSApplicationActivationPolicyRegular = 0,", header)
        self.assertIn("NSApplicationActivationPolicyAccessory = 1,", header)
        self.assertIn("NSApplicationActivationPolicyProhibited = 2,", header)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_nsimage_template_selectors_compile_in_both_objc_languages(self):
        path = "/documentation/appkit/nsimage"
        member = f"{path}/template"
        docc = DocC({
            path: {
                **page("NSImage", "class", declaration("@interface NSImage")),
                "topicSections": [{"identifiers": ["template"]}],
                "references": {"template": {"kind": "symbol", "role": "symbol", "url": member}},
            },
            member: page("template", "property", declaration("@property (getter=isTemplate) BOOL template;")),
        })
        symbols = [await parse_symbol(docc, name, "AppKit") for name in docc.pages]
        with tempfile.TemporaryDirectory() as directory:
            sdk = assemble_sdk(Path(directory), "macos", "26.5", {"AppKit": symbols})
            header = sdk / "System/Library/Frameworks/AppKit.framework/Headers/AppKit.h"
            for language, body in (
                ("objective-c", "image.template = 1; (void)image.isTemplate;"),
                ("objective-c++", "[image setTemplate:1]; (void)[image isTemplate];"),
            ):
                with self.subTest(language=language):
                    result = subprocess.run(
                        [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding",
                         "-fsyntax-only", "-Werror", "-isysroot", str(sdk),
                         "-include", str(header), "-x", language, "-"],
                        input=f"void use_image(NSImage *image) {{ {body} }}\n",
                        text=True, capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    async def test_enum_cases_use_their_own_names(self):
        path = "/documentation/contacts/cnauthorizationstatus"
        enum_name = "CNAuthorizationStatus"
        cases = {"restricted": "CNAuthorizationStatusRestricted", "authorized": "CNAuthorizationStatusAuthorized"}
        docc = DocC({
            path: {
                **page(enum_name, "enum", declaration(f"enum {enum_name} : NSInteger", "macOS")),
                "topicSections": [{"identifiers": list(cases)}],
                "references": {key: {"kind": "symbol", "role": "symbol", "url": f"{path}/{key}"}
                               for key in cases},
            },
            **{
                f"{path}/{key}": {"metadata": {
                    "title": key, "role": "symbol", "symbolKind": "case",
                    "externalID": f"c:@E@{enum_name}@{name}",
                }}
                for key, name in cases.items()
            },
        })
        symbols = [await parse_symbol(docc, key, "Contacts") for key in docc.pages]
        with tempfile.TemporaryDirectory() as directory:
            sdk = assemble_sdk(Path(directory), "macos", "26.5", {"Contacts": symbols})
            header = (sdk / "System/Library/Frameworks/Contacts.framework/Headers/Contacts.h").read_text()
        for case_name in cases.values():
            self.assertIn(f"    {case_name} =", header)
        self.assertNotIn(f"    {enum_name} =", header)

    async def test_uses_objc_symbol_kinds_and_children(self):
        root = "/documentation/foundation"
        alias = page("Color", "class", declaration("typedef struct Color * ColorRef;"))
        alias["variantOverrides"] = [{
            "traits": [{"interfaceLanguage": "occ"}],
            "patch": [{"op": "replace", "path": "/metadata/symbolKind", "value": "typealias"}],
        }]
        enum = page("Mode", "struct", declaration("enum Mode : int;"))
        enum["variantOverrides"] = [{
            "traits": [{"interfaceLanguage": "occ"}],
            "patch": [
                {"op": "replace", "path": "/metadata/symbolKind", "value": "enum"},
                {"op": "replace", "path": "/topicSections", "value": [{"identifiers": ["case"]}]},
            ],
        }]
        enum["references"] = {"case": {"kind": "symbol", "role": "symbol", "url": f"{root}/mode/on"}}
        case = page("ModeOn", "var", declaration("ModeOn"))
        case["variantOverrides"] = [{
            "traits": [{"interfaceLanguage": "occ"}],
            "patch": [{"op": "replace", "path": "/metadata/symbolKind", "value": "case"}],
        }]
        docc = DocC({f"{root}/color": alias, f"{root}/mode": enum, f"{root}/mode/on": case})
        symbols = await docc.symbols()
        self.assertEqual(symbols[0].kind.value, "class")
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", symbols).read_text()
        self.assertIn("typedef struct Color * ColorRef;", header)
        self.assertNotIn("@class Color;", header)
        self.assertIn("enum Mode : int {\n    ModeOn = 0,\n};", header)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_orders_c_types_and_renders_array_and_enum_declarators(self):
        root = "/documentation/foundation"
        state_ref = {
            "kind": "typeIdentifier", "text": "State", "preciseIdentifier": "c:@EA@State",
        }
        docc = DocC({
            f"{root}/handler": page("Handler", "typealias", {"languages": ["occ"], "tokens": [
                {"kind": "text", "text": "typedef void (^Handler)("},
                state_ref,
                {"kind": "text", "text": ");"},
            ]}),
            f"{root}/read": page("Read", "func", declaration("Point Read(void);")),
            f"{root}/address": page("Address", "typealias",
                                    declaration("typedef unsigned char[6] Address;")),
            f"{root}/state": {
                **page("State", "enum", declaration("typedef enum { ... } State;")),
                "topicSections": [{"identifiers": ["idle"]}],
                "references": {"idle": {"kind": "symbol", "role": "symbol",
                                        "url": f"{root}/state/idle"}},
            },
            f"{root}/state/idle": page("StateIdle", "case", declaration("StateIdle = 7")),
            f"{root}/point": page("Point", "struct", declaration("typedef struct Point { int x; } Point;")),
            f"{root}/error": page("Error", "enum", declaration("enum Error : int;")),
            f"{root}/opaque": page("Opaque", "enum", declaration("typedef enum { ... } Opaque;")),
            f"{root}/opaque/rawvalue": page("rawValue", "property", {
                "languages": ["swift"], "tokens": [{"kind": "text", "text": "var rawValue: Int32"}],
            }),
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding", "-fblocks",
                 "-fsyntax-only", "-Werror", "-include", str(header), "-x", "c", "-"],
                input=('_Static_assert(sizeof(Address) == 6, "array");\n'
                       '_Static_assert(StateIdle == 7, "explicit enum value");\n'
                       '_Static_assert(sizeof(Opaque) == 4, "raw enum width");\n'
                       '_Static_assert(sizeof(Read()) == sizeof(int), "record return");\n'
                       'Error error;\n'),
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_foundation_constant_values(self):
        pages = {}
        for name, kind, declaration_text, case, case_usr in (
            ("NSStringEncoding", "typealias", "typedef NSUInteger NSStringEncoding;",
             "NSUTF8StringEncoding", "c:@Ea@NSASCIIStringEncoding@NSUTF8StringEncoding"),
            ("NSSearchPathDirectory", "enum", "enum NSSearchPathDirectory : NSUInteger",
             "NSDocumentDirectory", "c:@E@NSSearchPathDirectory@NSDocumentDirectory"),
            ("NSSearchPathDomainMask", "enum", "enum NSSearchPathDomainMask : NSUInteger",
             "NSUserDomainMask", "c:@E@NSSearchPathDomainMask@NSUserDomainMask"),
        ):
            path = f"/documentation/foundation/{name.lower()}"
            child = f"{path}/{case.lower()}"
            pages[path] = {
                **page(name, kind, declaration(declaration_text, "macOS")),
                "topicSections": [{"identifiers": [case]}],
                "references": {case: {"kind": "symbol", "role": "symbol", "url": child}},
            }
            pages[child] = {"metadata": {
                "title": case, "role": "symbol", "symbolKind": "case", "externalID": case_usr,
            }}

        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await DocC(pages).symbols())
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding",
                 "-fsyntax-only", "-Werror", "-isysroot", str(header.parents[5]),
                 "-include", str(header), "-x", "objective-c", "-"],
                input=(
                    '_Static_assert(NSUTF8StringEncoding == 4, "UTF-8");\n'
                    '_Static_assert(NSDocumentDirectory == 9, "Documents");\n'
                    '_Static_assert(NSUserDomainMask == 1, "user domain");\n'
                ),
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            tbd = header.parents[1] / "Foundation.tbd"
            self.assertNotIn("_NSUTF8StringEncoding", tbd.read_text())

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_cf_linkage_macros_match_the_source_language(self):
        docc = DocC(address_pages("init(code:number:)"))
        source = (
            "CF_EXTERN_C_BEGIN\n"
            "void framework_probe(void);\n"
            "CF_EXTERN_C_END\n"
            "#ifdef __cplusplus\n"
            'extern "C" void framework_probe(void);\n'
            "#endif\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            for language in ("c", "c++", "objective-c", "objective-c++"):
                with self.subTest(language=language):
                    result = subprocess.run(
                        [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding",
                         "-fsyntax-only", "-Werror", "-include", str(header),
                         "-x", language, "-"],
                        input=source, text=True, capture_output=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)

    async def test_crawler_discovers_objc_only_exports(self):
        root = "/documentation/corefoundation"
        type_path = f"{root}/cftyperef"
        foreign = "/documentation/security/secrelease"
        names = {"cfgettypeid": "CFGetTypeID", "cfretain": "CFRetain", "cfrelease": "CFRelease"}
        docc = DocC({
            root: {
                "topicSections": [{"identifiers": ["type", "foreign"]}],
                "references": {
                    "type": {"kind": "symbol", "role": "symbol", "url": type_path},
                    "foreign": {"kind": "symbol", "role": "symbol", "url": foreign},
                },
            },
            type_path: {
                **page("CFTypeRef", "typealias", declaration("typedef const void *CFTypeRef;")),
                "references": {
                    name: {"kind": "symbol", "role": "symbol", "url": f"{root}/{name}"}
                    for name in names
                },
                "topicSections": [{"identifiers": ["cfgettypeid"]}],
                "variantOverrides": [{
                    "traits": [{"interfaceLanguage": "occ"}],
                    "patch": [{
                        "op": "replace",
                        "path": "/topicSections",
                        "value": [{"identifiers": ["cfretain", "cfrelease"]}],
                    }],
                }],
            },
            foreign: page("SecRelease", "func", declaration("void SecRelease(void);")),
            **{
                f"{root}/{path}": {"metadata": {
                    "title": name, "role": "symbol", "symbolKind": "func", "externalID": f"c:@F@{name}",
                }}
                for path, name in names.items()
            },
        })
        framework = FrameworkInfo("CoreFoundation", f"doc://test{root}", ["swift", "occ"], "")
        paths = await crawl_framework_symbols(docc, framework)
        symbols = [await parse_symbol(docc, path, framework.name) for path in paths]
        with tempfile.TemporaryDirectory() as directory:
            sdk = assemble_sdk(Path(directory), "macos", "26.0", {framework.name: symbols})
            stub = sdk / "System/Library/Frameworks/CoreFoundation.framework/CoreFoundation.tbd"
            exports = stub.read_text()

        for name in names.values():
            self.assertIn(f"_{name}", exports)
        self.assertNotIn(foreign, paths)

    async def test_imports_follow_objc_type_references(self):
        nsstring = {
            "languages": ["occ"],
            "tokens": [
                {"kind": "text", "text": "@interface NSString : "},
                {
                    "kind": "typeIdentifier",
                    "text": "NSObject",
                    "identifier": "doc://com.apple.documentation/documentation/ObjectiveC/NSObject-swift.class",
                    "preciseIdentifier": "c:objc(cs)NSObject",
                },
            ],
        }
        c_type = {
            "languages": ["occ"],
            "tokens": [
                {"kind": "text", "text": "typedef "},
                {
                    "kind": "typeIdentifier",
                    "text": "CGPoint",
                    "identifier": "doc://com.apple.coregraphics/documentation/CoreGraphics/CGPoint",
                },
                {"kind": "text", "text": " Position;"},
            ],
        }
        docc = DocC({
            "/documentation/foundation/nsstring": {
                **page("NSString", "class", nsstring),
                "relationshipsSections": [
                    {"type": "inheritsFrom", "identifiers": [nsstring["tokens"][1]["identifier"]]},
                    {"type": "conformsTo", "identifiers": [
                        "doc://com.apple.documentation/documentation/CloudKit/CKRecordValue-c.protocol",
                        "doc://com.apple.documentation/documentation/Swift/Sendable",
                    ]},
                ],
            },
            "/documentation/foundation/position": page("Position", "typealias", c_type),
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols()).read_text()

        self.assertEqual(
            [line for line in header.splitlines() if line.startswith("#import <")],
            ["#import <CoreGraphics/CoreGraphics.h>", "#import <objc/NSObject.h>"],
        )
        self.assertIn("@interface NSString : NSObject\n", header)

    async def test_forward_declarations_use_selected_objc_symbols(self):
        docc = DocC({
            "/documentation/foundation/nsdictionary/iterator": page(
                "NSDictionary.Iterator", "class",
                {**declaration("final class Iterator"), "languages": ["swift"]},
            ),
            "/documentation/combine/publisher": page(
                "Publisher", "protocol",
                {**declaration("protocol Publisher"), "languages": ["swift"]},
            ),
            "/documentation/foundation/mobileonly": page(
                "MobileOnly", "class", declaration("@interface MobileOnly", "iOS"),
            ),
            "/documentation/foundation/nsstring": page(
                "NSString", "class", declaration("@interface NSString", "macOS"),
            ),
            "/documentation/foundation/nscopying": page(
                "NSCopying", "protocol", declaration("@protocol NSCopying"),
            ),
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols()).read_text()

        self.assertIn("@class NSString;", header)
        self.assertIn("@protocol NSCopying;", header)
        self.assertNotIn("@class NSDictionary.Iterator;", header)
        self.assertNotIn("@protocol Publisher;", header)

    async def test_imports_use_installed_c_headers(self):
        parameters = {
            "languages": ["occ"],
            "tokens": [
                {"kind": "text", "text": "void UseTypes("},
                {"kind": "typeIdentifier", "text": "CFStringRef",
                 "identifier": "doc://com.apple.corefoundation/documentation/corefoundation/cfstring"},
                {"kind": "text", "text": " string, "},
                {"kind": "typeIdentifier", "text": "dispatch_queue_t",
                 "identifier": "doc://com.apple.dispatch/documentation/Dispatch/dispatch_queue_t"},
                {"kind": "text", "text": " queue, "},
                {"kind": "typeIdentifier", "text": "mach_port_t",
                 "identifier": "doc://com.apple.documentation/documentation/kernel/mach_port_t",
                 "preciseIdentifier": "c:@T@mach_port_t"},
                {"kind": "text", "text": " port, "},
                {"kind": "typeIdentifier", "text": "kern_return_t",
                 "identifier": "doc://com.apple.driverkit/documentation/DriverKit/kern_return_t",
                 "preciseIdentifier": "c:@T@kern_return_t"},
                {"kind": "text", "text": " status, "},
                {"kind": "typeIdentifier", "text": "task_id_token_t",
                 "identifier": "doc://com.apple.documentation/documentation/kernel/task_id_token_t",
                 "preciseIdentifier": "c:@T@task_id_token_t"},
                {"kind": "text", "text": " identity, "},
                {"kind": "typeIdentifier", "text": "size_t",
                 "identifier": "doc://com.apple.documentation/documentation/kernel/size_t",
                 "preciseIdentifier": "c:@T@size_t"},
                {"kind": "text", "text": " size, "},
                {"kind": "typeIdentifier", "text": "pid_t",
                 "identifier": "doc://com.apple.documentation/documentation/DriverKit/pid_t",
                 "preciseIdentifier": "c:@T@pid_t"},
                {"kind": "text", "text": " process, "},
                {"kind": "typeIdentifier", "text": "int8_t",
                 "identifier": "doc://com.apple.documentation/documentation/kernel/int8_t",
                 "preciseIdentifier": "c:@T@int8_t"},
                {"kind": "text", "text": " byte, "},
                {"kind": "typeIdentifier", "text": "uint16_t",
                 "identifier": "doc://com.apple.documentation/documentation/kernel/uint16_t",
                 "preciseIdentifier": "c:@T@uint16_t"},
                {"kind": "text", "text": " value, "},
                {"kind": "typeIdentifier", "text": "au_asid_t",
                 "identifier": "doc://com.apple.documentation/documentation/kernel/au_asid_t",
                 "preciseIdentifier": "c:@T@au_asid_t"},
                {"kind": "text", "text": " audit_session, "},
                {"kind": "typeIdentifier", "text": "vector_int2",
                 "identifier": "doc://com.apple.documentation/documentation/kernel/vector_int2",
                 "preciseIdentifier": "c:@T@vector_int2"},
                {"kind": "text", "text": " pixels, "},
                {"kind": "typeIdentifier", "text": "simd_quatf",
                 "identifier": "doc://com.apple.documentation/documentation/simd/simd_quatf",
                 "preciseIdentifier": "c:@T@simd_quatf"},
                {"kind": "text", "text": " rotation);"},
            ],
        }
        docc = DocC({"/documentation/foundation/usetypes": page("UseTypes", "func", parameters)})
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols()).read_text()

        self.assertEqual(
            [line for line in header.splitlines() if line.startswith("#import <")],
            ["#import <CoreFoundation/CoreFoundation.h>", "#import <bsm/audit.h>",
             "#import <dispatch/dispatch.h>", "#import <mach/kern_return.h>",
             "#import <mach/mach_types.h>", "#import <mach/port.h>",
             "#import <simd/simd.h>", "#import <stddef.h>", "#import <stdint.h>", "#import <sys/types.h>"],
        )

    async def test_c_function_availability_precedes_the_semicolon(self):
        docc = DocC({
            "/documentation/foundation/lookup": {
                **page("Lookup", "func", declaration("void Lookup(void);", "macOS")),
                "metadata": {"title": "Lookup", "role": "symbol", "symbolKind": "func",
                             "platforms": [{"name": "macOS", "introducedAt": "11.0"}]},
            },
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols()).read_text()

        self.assertIn("void Lookup(void) API_AVAILABLE(macos(11.0));", header)
        self.assertNotIn("@class MobileOnly;", header)

    async def test_objc_runtime_types_use_the_compat_preamble(self):
        flag = {"languages": ["occ"], "tokens": [
            {"kind": "text", "text": "typedef "},
            {
                "kind": "typeIdentifier",
                "text": "BOOL",
                "identifier": "doc://com.apple.documentation/documentation/ObjectiveC/BOOL",
                "preciseIdentifier": "c:@T@BOOL",
            },
            {"kind": "text", "text": " Flag;"},
        ]}
        docc = DocC({"/documentation/foundation/flag": page("Flag", "typealias", flag)})
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols()).read_text()
        self.assertIn("typedef BOOL Flag;", header)
        self.assertNotIn("ObjectiveC/ObjectiveC.h", header)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_foreign_objc_pointer_does_not_import_its_umbrella(self):
        image = {
            "kind": "typeIdentifier",
            "text": "NSImage",
            "identifier": "doc://com.apple.appkit/documentation/AppKit/NSImage",
            "preciseIdentifier": "c:objc(cs)NSImage",
        }
        signature = {"languages": ["occ"], "tokens": [
            {"kind": "text", "text": "extern "},
            image,
            {"kind": "text", "text": " *copyImage(void);"},
        ]}
        docc = DocC({
            "/documentation/foundation/copyimage": page("copyImage", "func", signature),
        })
        clang_resources = Path(subprocess.check_output(
            [CLANG, "-print-resource-dir"], text=True,
        ).strip())
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            framework_dir = header.parents[2]
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos11",
                 "-ffreestanding", "-fsyntax-only", "-Werror",
                 "-isysroot", str(header.parents[5]), "-nostdinc",
                 "-isystem", str(clang_resources / "include"),
                 "-F", str(framework_dir), "-x", "objective-c", "-"],
                input="#import <Foundation/Foundation.h>\nNSImage *image(void) { return copyImage(); }\n",
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            docc.pages["/documentation/foundation/subimage"] = page(
                "SubImage", "class",
                {"languages": ["occ"], "tokens": [
                    {"kind": "text", "text": "@interface SubImage : "}, image,
                ]},
            )
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            self.assertIn("#import <AppKit/AppKit.h>", header.read_text())

    async def test_separates_return_type_from_function_name(self):
        # DocC's CFRetain declaration has no whitespace token before CFRetain.
        retain_declaration = {
            "languages": ["occ"],
            "tokens": [
                {"kind": "keyword", "text": "extern"},
                {"kind": "text", "text": " "},
                {"kind": "typeIdentifier", "text": "CFTypeRef"},
                {"kind": "identifier", "text": "CFRetain"},
                {"kind": "text", "text": "("},
                {"kind": "typeIdentifier", "text": "CFTypeRef"},
                {"kind": "text", "text": " "},
                {"kind": "internalParam", "text": "cf"},
                {"kind": "text", "text": ");"},
            ],
        }
        docc = DocC({
            "/documentation/corefoundation/cfretain": page("CFRetain", "func", retain_declaration),
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols()).read_text()
        self.assertIn("extern CFTypeRef CFRetain(CFTypeRef cf);", header)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_renders_callback_typedefs_with_names_inside_the_declarator(self):
        docc = DocC({
            "/documentation/foundation/callback": page(
                "Callback", "typealias", declaration("typedef void (*)(void *, void *) Callback;"),
            ),
            "/documentation/foundation/handler": page(
                "Handler", "typealias", declaration("typedef void (^)(int) Handler;"),
            ),
            "/documentation/foundation/already-named": page(
                "AlreadyNamed", "typealias", declaration("typedef void (*AlreadyNamed)(void);"),
            ),
        })
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding", "-fblocks",
                 "-fsyntax-only", "-Werror", "-include", str(header), "-x", "c", "-"],
                input="int main(void) { Callback c = 0; Handler h = 0; AlreadyNamed n = 0; return c || h || n; }",
                text=True, capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    async def test_uses_platform_variant_before_unqualified_declaration(self):
        docc = DocC({
            "/documentation/foundation/handle": page(
                "Handle", "typealias",
                declaration("typedef struct Generic *Handle;"),
                declaration("typedef struct Mobile *Handle;", "iOS"),
                declaration("typedef struct Desktop *Handle;", "macOS"),
            ),
        })
        symbols = await docc.symbols()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            macos = assemble_header(root, "macos", symbols).read_text()
        self.assertIn("typedef struct Desktop *Handle;", macos)
        self.assertNotIn("typedef struct Mobile *Handle;", macos)
        self.assertNotIn("typedef struct Generic *Handle;", macos)

    @unittest.skipUnless(CLANG, "requires Clang")
    async def test_struct_offsets_follow_memberwise_initializer(self):
        docc = DocC(address_pages("init(code:number:)"))
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols())
            result = subprocess.run(
                [CLANG, "-target", "arm64-apple-macos11", "-ffreestanding",
                 "-std=c11", "-fsyntax-only", "-Werror", "-include", str(header),
                 "-x", "c", "-"],
                input=(
                    '_Static_assert(__builtin_offsetof(Address, code) == 0, "code");\n'
                    '_Static_assert(__builtin_offsetof(Address, number) == 4, "number");\n'
                ),
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    async def test_incomplete_initializer_leaves_struct_opaque(self):
        docc = DocC(address_pages("init(code:)"))
        with tempfile.TemporaryDirectory() as directory:
            header = assemble_header(Path(directory), "macos", await docc.symbols()).read_text()
        self.assertIn("typedef struct Address Address;", header)
        self.assertNotIn("struct Address {", header)
