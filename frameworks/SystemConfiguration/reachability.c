#include <SystemConfiguration/SCNetworkReachability.h>

#include "../test-abi.h"

FUNCTION_TYPE(SCNetworkReachabilityCreateWithName, SCNetworkReachabilityRef,
              CFAllocatorRef, const char *);
