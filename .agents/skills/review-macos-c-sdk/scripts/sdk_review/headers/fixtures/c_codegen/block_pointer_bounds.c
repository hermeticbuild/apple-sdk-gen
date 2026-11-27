#include <ptrcheck.h>
#include <Block.h>

#if !__has_feature(bounds_safety)
#error This fixture requires bounds safety
#endif

#if defined(TEST_UNSAFE_RAW_RELEASE)
void raw_release(const void *__unsafe_indexable block) {
    _Block_release(block);
}
#else
void *__single copy_one(const void *__single block) {
    return _Block_copy(block);
}

void wrapped_release(const void *__unsafe_indexable block) {
    Block_release(block);
}
#endif
