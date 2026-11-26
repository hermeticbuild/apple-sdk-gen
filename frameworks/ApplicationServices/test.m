#include <ApplicationServices/ApplicationServices.h>
#include <stddef.h>

_Static_assert(sizeof(LSLaunchURLSpec) == 36, "LSLaunchURLSpec size");
_Static_assert(_Alignof(LSLaunchURLSpec) == 2, "LSLaunchURLSpec alignment");
_Static_assert(offsetof(LSLaunchURLSpec, appURL) == 0, "appURL offset");
_Static_assert(offsetof(LSLaunchURLSpec, itemURLs) == 8, "itemURLs offset");
_Static_assert(offsetof(LSLaunchURLSpec, passThruParams) == 16, "passThruParams offset");
_Static_assert(offsetof(LSLaunchURLSpec, launchFlags) == 24, "launchFlags offset");
_Static_assert(offsetof(LSLaunchURLSpec, asyncRefCon) == 28, "asyncRefCon offset");
_Static_assert(kLSRolesAll == 0xffffffffu, "all roles");
_Static_assert(kLSLaunchDefaults == 1, "launch defaults");

int main(void) {
    CFArrayRef apps = LSCopyApplicationURLsForBundleIdentifier(
        CFSTR("com.apple.finder"), NULL);
    if (!apps)
        return 1;
    int failed = CFArrayGetCount(apps) == 0 ||
                 !UTTypeEqual(kUTTypeXML, CFSTR("public.xml"));
    CFRelease(apps);
    return failed;
}
