#include <SystemConfiguration/SystemConfiguration.h>

int main(void) {
    SCNetworkReachabilityRef reachability = SCNetworkReachabilityCreateWithName(NULL, "localhost");
    if (!reachability)
        return 1;
    CFRelease(reachability);

    SCPreferencesRef preferences = SCPreferencesCreate(NULL, CFSTR("probe"), NULL);
    if (!preferences)
        return 1;
    CFRelease(preferences);
    return 0;
}
