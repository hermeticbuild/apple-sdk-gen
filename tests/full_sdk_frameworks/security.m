#import <Security/Security.h>

int main(void) {
    CFStringRef message = SecCopyErrorMessageString(errSecSuccess, NULL);
    if (!message)
        return 1;
    int failed = CFStringGetLength(message) == 0;
    CFRelease(message);
    return failed;
}
