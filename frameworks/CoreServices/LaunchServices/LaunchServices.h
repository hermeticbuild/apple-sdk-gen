#ifndef HERMETIC_CORE_SERVICES_LAUNCHSERVICES_H
#define HERMETIC_CORE_SERVICES_LAUNCHSERVICES_H
#include <CoreFoundation/CFArray.h>
#include <CoreFoundation/CFError.h>
#include <CoreFoundation/CFURL.h>
#include <MacTypes.h>
#include "UTType.h"

typedef OptionBits LSLaunchFlags;
typedef OptionBits LSRolesMask;
enum { kLSLaunchDefaults = 1 };
enum { kLSRolesAll = (UInt32)0xffffffff };
struct AEDesc;

/* The LaunchServices ABI uses two-byte packing on both macOS targets. */
#pragma pack(push, 2)
typedef struct LSLaunchURLSpec {
    CFURLRef appURL;
    CFArrayRef itemURLs;
    const struct AEDesc *passThruParams;
    LSLaunchFlags launchFlags;
    void *asyncRefCon;
} LSLaunchURLSpec;
#pragma pack(pop)

CF_EXTERN_C_BEGIN
CF_EXPORT OSStatus LSOpenFromURLSpec(const LSLaunchURLSpec *spec, CFURLRef *launchedURL);
CF_EXPORT CFArrayRef LSCopyApplicationURLsForBundleIdentifier(CFStringRef identifier, CFErrorRef *error);
CF_EXPORT CFArrayRef LSCopyAllHandlersForURLScheme(CFStringRef scheme);
CF_EXPORT CFArrayRef LSCopyAllRoleHandlersForContentType(CFStringRef type, LSRolesMask roles);
CF_EXPORT CFURLRef LSCopyDefaultApplicationURLForContentType(CFStringRef type, LSRolesMask roles, CFErrorRef *error);
CF_EXPORT CFStringRef LSCopyDefaultHandlerForURLScheme(CFStringRef scheme);
CF_EXTERN_C_END
#endif
