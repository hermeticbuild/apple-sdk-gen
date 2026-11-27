# SDK tests

| Suite | Input | What it checks |
| --- | --- | --- |
| [C header installation](c_header_installation/) | Standalone tree from `make install` | Public header inclusion, C declarations and ABI, XNU source receipts, and stage merging |
| [Minimal SDK linking](minimal_sdk_linking/) | Extracted minimal SDK | C programs link and run with the shipped stubs, and the linker reports Foundation as absent |
| [Full SDK frameworks](full_sdk_frameworks/) | Assembled full SDK | Framework headers, Objective-C++ modules, and runtime symbols work for compiled clients |
| [SDK archives](sdk_archives/) | Both release archives or small fixture trees | Reproducible packaging and agreement on shared files, with the expected minimal SDK contents |

`make test SDK=macosx26.5 OUT="$C_INSTALL"` runs the standalone C suite.
`make test-composed-sdk SDK=macosx26.5` runs it and the archive, link, and
framework checks. See [the SDK test commands](../docs/composed-sdk-tests.md)
for running a single suite.

The [generator tests](../tools/apple_sdk_gen/tests/) use small DocC inputs
to check generated headers and stubs. `make test-python` runs those and the
archive packer tests. The [Bazel workspaces](../e2e/) use the released SDK
format to build real consumers.
