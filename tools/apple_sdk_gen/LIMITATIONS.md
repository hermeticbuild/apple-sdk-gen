# macOS SDK coverage and limitations

The release build combines pinned Apple open-source headers, versioned
Darwin linker stubs, framework declarations from Apple’s DocC data, and
local framework recipes. DocC supplies API declarations, availability, and
references to related symbols. It leaves out some details needed for
compilation, linking, and ABI compatibility.

## What the build supplies

- [The C components](../../components/README.md) install headers from
  pinned sources, including Libc, XNU, and libpthread. The recipes run
  upstream install rules where possible, apply documented local changes,
  and record each installed header in `header-manifest.tsv`. Both archives
  include these headers, the DocC-derived SIMD header, and system linker
  stubs for the selected SDK version.
- The Full archive adds the objc4 runtime headers, upstream LLVM libc++
  and libc++abi headers, and framework bundles. The composer copies
  generated frameworks, uses prepared bundles where a local recipe
  supplies one, and overlays specific files for IOKit and Security.
  See the [release build](../../release/README.md) and
  [framework recipes](../../frameworks/).
- The standalone DocC command writes an intermediate SDK tree. Use the
  composed archives as compiler sysroots. See the
  [archive layout and build commands](../../README.md#output-layout).

## What still needs evidence

| Area | Current behavior and remaining limitation |
| --- | --- |
| C records | The generator keeps complete C declarations. For abbreviated records, it reads member declarations and uses a documented memberwise initializer when its argument labels give one unambiguous order for all the recovered fields. It can use Swift DocC data to recover missing C field types. A record with insufficient evidence retains a declaration without a body, so clients may be unable to access fields or pass the type by value. |
| Enum values | The generator uses explicit DocC values and a [table of known values](supplements/enum_values.py). Some enum forms still fall back to sequential or bitmask values. For abbreviated enum bodies it skips cases without value evidence. Code that relies on numeric values needs coverage for the specific constants it uses. |
| Macros and inline functions | Generated framework umbrellas supply a compatibility preamble and [selected inline implementations](supplements/inline_functions.py). The framework recipes supply additional definitions where needed. DocC can omit macro expansions and function bodies. An inline function also needs to stay out of the linker export list when it has no external definition. |
| Objective-C categories | DocC can list category methods on a class without exposing the category’s owning framework. This can introduce cross-framework imports and import cycles. Framework recipes supply focused declarations where those problems affect consumers. |
| Framework exports | DocC declarations provide candidate linker symbols. They do not establish which symbols a dylib exports or reexports, or what install name it uses. Some generated framework stubs have incomplete exports or placeholders. The [Darwin inventory](supplements/data/darwin_macos_26.5.md) records separate source evidence for the system and runtime stubs it covers. |
| Framework headers | Generated per-name headers generally import their framework’s umbrella. The umbrella carries the declarations. A successful import of a forwarding header does not establish that every declaration from the corresponding Apple header is present. Prepared bundles have the coverage and provenance documented by their recipes. |

The [SDK tests](../../tests/README.md) exercise the archived headers and
linker stubs. The [consumer tests](../../e2e/README.md) show the builds
covered by the current test suite.
