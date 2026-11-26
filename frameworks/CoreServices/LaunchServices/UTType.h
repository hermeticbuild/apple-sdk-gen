#ifndef HERMETIC_CORE_SERVICES_UTTYPE_H
#define HERMETIC_CORE_SERVICES_UTTYPE_H
#include <CoreFoundation/CFString.h>

CF_EXTERN_C_BEGIN
CF_EXPORT Boolean UTTypeEqual(CFStringRef left, CFStringRef right);
CF_EXPORT Boolean UTTypeConformsTo(CFStringRef type, CFStringRef parent);
CF_EXPORT CFStringRef UTTypeCopyDescription(CFStringRef type);
CF_EXPORT CFStringRef UTTypeCreatePreferredIdentifierForTag(CFStringRef tagClass, CFStringRef tag, CFStringRef parent);
CF_EXPORT CFStringRef UTTypeCopyPreferredTagWithClass(CFStringRef type, CFStringRef tagClass);
CF_EXPORT const CFStringRef kUTTagClassFilenameExtension;
CF_EXPORT const CFStringRef kUTTagClassMIMEType;
CF_EXPORT const CFStringRef kUTTypeApplication;
CF_EXPORT const CFStringRef kUTTypeFolder;
CF_EXPORT const CFStringRef kUTTypeVolume;
CF_EXPORT const CFStringRef kUTTypeXML;
CF_EXTERN_C_END
#endif
