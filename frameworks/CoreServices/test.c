#include <CoreServices/CoreServices.h>

int main(void) {
    CFStringRef type = UTTypeCreatePreferredIdentifierForTag(
        kUTTagClassFilenameExtension, CFSTR("xml"), NULL);
    if (!type)
        return 1;
    int failed = !UTTypeEqual(type, kUTTypeXML) ||
                 !UTTypeConformsTo(type, CFSTR("public.text"));
    CFRelease(type);
    return failed;
}
