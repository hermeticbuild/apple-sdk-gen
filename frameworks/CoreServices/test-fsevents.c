#include <CoreServices/CoreServices.h>
#include <stddef.h>

_Static_assert(sizeof(FSEventStreamEventId) == 8, "event ID ABI");
_Static_assert(sizeof(FSEventStreamContext) == 40, "context ABI");
_Static_assert(offsetof(FSEventStreamContext, copyDescription) == 32, "context callback ABI");
_Static_assert(kFSEventStreamCreateFlagFileEvents == 0x10, "create flags ABI");
_Static_assert(kFSEventStreamEventFlagItemCloned == 0x00400000, "event flags ABI");

static void changed(ConstFSEventStreamRef stream, void *info, size_t count,
                    void *paths, const FSEventStreamEventFlags *flags,
                    const FSEventStreamEventId *ids) {}

int main(void) {
    const void *directory = CFSTR("/tmp");
    CFArrayRef paths = CFArrayCreate(NULL, &directory, 1, &kCFTypeArrayCallBacks);
    FSEventStreamContext context = {0};
    FSEventStreamRef stream = FSEventStreamCreate(NULL, changed, &context, paths,
        kFSEventStreamEventIdSinceNow, 0.1, kFSEventStreamCreateFlagFileEvents);
    CFRelease(paths);
    if (!stream)
        return 1;
    FSEventStreamSetDispatchQueue(stream, dispatch_get_global_queue(0, 0));
    Boolean started = FSEventStreamStart(stream);
    if (started)
        FSEventStreamStop(stream);
    FSEventStreamInvalidate(stream);
    FSEventStreamRelease(stream);
    return !started;
}
