#import <AppKit/NSText.h>

#if defined(__arm64__)
_Static_assert(NSTextAlignmentCenter == 1 && NSTextAlignmentRight == 2, "Apple silicon text ABI");
#elif defined(__x86_64__)
_Static_assert(NSTextAlignmentCenter == 2 && NSTextAlignmentRight == 1, "Intel text ABI");
#else
#error unsupported macOS client architecture
#endif
