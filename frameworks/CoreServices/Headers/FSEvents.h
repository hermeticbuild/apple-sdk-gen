#pragma once

#include <CoreFoundation/CoreFoundation.h>
#include <dispatch/dispatch.h>
#include <stdint.h>

/* C declarations from Apple's FSEvents DocC pages. Git's Darwin fsmonitor
 * fallback corroborates the flag values and context layout. */
typedef struct __FSEventStream *FSEventStreamRef;
typedef const struct __FSEventStream *ConstFSEventStreamRef;
typedef uint32_t FSEventStreamCreateFlags;
typedef uint32_t FSEventStreamEventFlags;
typedef uint64_t FSEventStreamEventId;

typedef struct FSEventStreamContext {
    CFIndex version;
    void *info;
    CFAllocatorRetainCallBack retain;
    CFAllocatorReleaseCallBack release;
    CFAllocatorCopyDescriptionCallBack copyDescription;
} FSEventStreamContext;

typedef void (*FSEventStreamCallback)(ConstFSEventStreamRef stream, void *info,
    size_t count, void *paths, const FSEventStreamEventFlags *flags,
    const FSEventStreamEventId *ids);

#define kFSEventStreamEventIdSinceNow UINT64_MAX

enum {
    kFSEventStreamCreateFlagNoDefer = 0x02,
    kFSEventStreamCreateFlagWatchRoot = 0x04,
    kFSEventStreamCreateFlagFileEvents = 0x10,
};

enum {
    kFSEventStreamEventFlagNone = 0x00000000,
    kFSEventStreamEventFlagMustScanSubDirs = 0x00000001,
    kFSEventStreamEventFlagUserDropped = 0x00000002,
    kFSEventStreamEventFlagKernelDropped = 0x00000004,
    kFSEventStreamEventFlagEventIdsWrapped = 0x00000008,
    kFSEventStreamEventFlagHistoryDone = 0x00000010,
    kFSEventStreamEventFlagRootChanged = 0x00000020,
    kFSEventStreamEventFlagMount = 0x00000040,
    kFSEventStreamEventFlagUnmount = 0x00000080,
    kFSEventStreamEventFlagItemCreated = 0x00000100,
    kFSEventStreamEventFlagItemRemoved = 0x00000200,
    kFSEventStreamEventFlagItemInodeMetaMod = 0x00000400,
    kFSEventStreamEventFlagItemRenamed = 0x00000800,
    kFSEventStreamEventFlagItemModified = 0x00001000,
    kFSEventStreamEventFlagItemFinderInfoMod = 0x00002000,
    kFSEventStreamEventFlagItemChangeOwner = 0x00004000,
    kFSEventStreamEventFlagItemXattrMod = 0x00008000,
    kFSEventStreamEventFlagItemIsFile = 0x00010000,
    kFSEventStreamEventFlagItemIsDir = 0x00020000,
    kFSEventStreamEventFlagItemIsSymlink = 0x00040000,
    kFSEventStreamEventFlagOwnEvent = 0x00080000,
    kFSEventStreamEventFlagItemIsHardlink = 0x00100000,
    kFSEventStreamEventFlagItemIsLastHardlink = 0x00200000,
    kFSEventStreamEventFlagItemCloned = 0x00400000,
};

CF_EXTERN_C_BEGIN
CF_EXPORT FSEventStreamRef FSEventStreamCreate(CFAllocatorRef allocator,
    FSEventStreamCallback callback, FSEventStreamContext *context,
    CFArrayRef paths, FSEventStreamEventId since, CFTimeInterval latency,
    FSEventStreamCreateFlags flags);
CF_EXPORT FSEventStreamEventId FSEventsGetCurrentEventId(void);
CF_EXPORT void FSEventStreamSetDispatchQueue(FSEventStreamRef stream, dispatch_queue_t queue);
CF_EXPORT Boolean FSEventStreamStart(FSEventStreamRef stream);
CF_EXPORT void FSEventStreamStop(FSEventStreamRef stream);
CF_EXPORT void FSEventStreamInvalidate(FSEventStreamRef stream);
CF_EXPORT void FSEventStreamRelease(FSEventStreamRef stream);
CF_EXTERN_C_END
