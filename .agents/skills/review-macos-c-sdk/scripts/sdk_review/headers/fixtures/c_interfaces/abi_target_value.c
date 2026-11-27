#include <TargetConditionals.h>

#if defined(__arm64__)
_Static_assert(TARGET_ABI_USES_IOS_VALUES == 1, "arm64 macOS uses iOS enum values");
#elif defined(__x86_64__)
_Static_assert(TARGET_ABI_USES_IOS_VALUES == 0, "Intel macOS uses Intel enum values");
#else
#error unsupported macOS client architecture
#endif
