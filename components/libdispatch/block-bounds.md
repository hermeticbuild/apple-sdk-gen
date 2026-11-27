# Blocks runtime pointer bounds

The macOS 26.5 recipe derives `Block.h` from the pinned libdispatch
`src/BlocksRuntime/Block.h`. The upstream header declares the copy and
release operations on a single block and preserves the caller's block type in
the wrappers. Its license notice is retained. The libclosure public header
contains an unresolved license placeholder and is excluded from the recipe.

Under Clang bounds checking, a raw copy accepts a single block pointer and
returns a single pointer. A raw release takes a single pointer. The typed
wrappers form the boundary where the block is explicitly converted. The local
patch uses Clang's documented pointer annotations and forge operation. The
ordinary compiler path still evaluates the argument once and emits the same
calls. [Clang bounds safety](https://clang.llvm.org/docs/BoundsSafety.html)

Use the [pointer bounds procedure](../../.agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/c_interface_review.md#qualify-blockh-pointer-bounds)
for the positive and negative Apple Clang checks.
