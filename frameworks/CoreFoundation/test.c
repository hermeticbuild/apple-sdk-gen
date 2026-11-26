#include <CoreFoundation/CoreFoundation.h>

CF_ENUM(UInt32) { kProbeCode = 42 };
typedef CF_CLOSED_ENUM(UInt32, ProbeState) { kProbeStateReady = 1 };

typedef CFStringRef ProbeIdentifier CF_STRING_ENUM;
enum {
    kProbeAvailable CF_ENUM_AVAILABLE(10_15, 13_0) = 1,
    kProbeOld CF_ENUM_DEPRECATED(10_15, 15_0, 13_0, 18_0, "Use kProbeAvailable") = 2,
};

CF_ASSUME_NONNULL_BEGIN
static CFErrorDomain error_domain(CFErrorRef error) CF_SWIFT_NAME(probeDomain(_:)) {
    return CFErrorGetDomain(error);
}
CF_ASSUME_NONNULL_END

int main(void) {
    if (CFPreferencesAppValueIsForced(CFSTR("sdk.managed.preference.probe"), CFSTR("org.hermeticbuild.sdk-probe")))
        return 1;
    ProbeIdentifier domain = CFStringCreateCopy(NULL, CFSTR("Framework linkage"));
    if (!domain)
        return 1;
    CFErrorRef error = CFErrorCreate(NULL, domain, kProbeCode, NULL);
    if (!error) {
        CFRelease(domain);
        return 1;
    }
    CFTypeRef retained = CFRetain(error);
    int failed = retained != error || !CFEqual(error_domain(error), domain);
    CFRelease(retained);
    CFRelease(error);
    CFRelease(domain);
    return failed;
}
