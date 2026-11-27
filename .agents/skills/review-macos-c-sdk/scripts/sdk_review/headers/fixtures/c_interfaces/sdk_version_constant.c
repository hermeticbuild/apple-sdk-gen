#include <Availability.h>

#define REVIEW_MAC_VERSION_JOIN(major, minor) __MAC_##major##_##minor
#define REVIEW_MAC_VERSION_NAME(major, minor) REVIEW_MAC_VERSION_JOIN(major, minor)

_Static_assert(REVIEW_MAC_VERSION_NAME(REVIEW_SDK_MAJOR, REVIEW_SDK_MINOR) == REVIEW_SDK_FLOOR,
               "SDK version constant");
