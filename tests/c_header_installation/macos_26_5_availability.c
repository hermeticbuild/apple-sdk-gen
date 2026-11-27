#include <Availability.h>
#include <sys/cdefs.h>

_Static_assert(__MAC_26_5 == 260500, "missing macOS 26.5 availability constant");
_Static_assert(__MAC_OS_X_VERSION_MAX_ALLOWED == 260500, "wrong macOS SDK availability ceiling");
_Static_assert((0 __DARWIN_ALIAS_STARTING(__MAC_26_5, __IPHONE_17_0, +1)) ==
               (__ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__ >= 260500),
               "XNU alias selector disagrees with the macOS deployment minimum");
_Static_assert(__MAC_OS_X_VERSION_MIN_REQUIRED == __ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__,
               "SDK availability ceiling changed the deployment minimum");
#ifdef __MAC_26_6
#error "macOS 26.5 headers expose a newer SDK's availability constant"
#endif
