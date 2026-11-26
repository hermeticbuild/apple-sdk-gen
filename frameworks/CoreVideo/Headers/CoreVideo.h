#pragma once

#include <CoreFoundation/CFBase.h>
#include <CoreFoundation/CFDictionary.h>

typedef struct __CVBuffer *CVBufferRef;
typedef CVBufferRef CVImageBufferRef;
typedef CVImageBufferRef CVPixelBufferRef;
typedef int32_t CVReturn;
typedef uint64_t CVOptionFlags;
typedef CVOptionFlags CVPixelBufferLockFlags;
typedef void (*CVPixelBufferReleaseBytesCallback)(void *context, const void *baseAddress);

enum {
    kCVReturnSuccess = 0,
    kCVPixelFormatType_24RGB = 24,
    kCVPixelFormatType_32BGRA = 0x42475241,
    kCVPixelFormatType_422YpCbCr8 = 0x32767579,
    kCVPixelFormatType_420YpCbCr8BiPlanarFullRange = 0x34323066,
    kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange = 0x34323076,
    kCVPixelBufferLock_ReadOnly = 1,
};

CF_EXTERN_C_BEGIN
CF_EXPORT CFStringRef const kCVPixelBufferWidthKey;
CF_EXPORT CFStringRef const kCVPixelBufferHeightKey;
CF_EXPORT CFStringRef const kCVPixelBufferPixelFormatTypeKey;

CF_EXPORT CVBufferRef CVBufferRetain(CVBufferRef buffer);
CF_EXPORT void CVBufferRelease(CVBufferRef buffer);
CF_EXPORT CVPixelBufferRef CVPixelBufferRetain(CVPixelBufferRef buffer);
CF_EXPORT void CVPixelBufferRelease(CVPixelBufferRef buffer);

CF_EXPORT CVReturn CVPixelBufferCreate(CFAllocatorRef allocator, size_t width, size_t height,
                                      OSType pixelFormat, CFDictionaryRef attributes,
                                      CVPixelBufferRef *buffer);
CF_EXPORT CVReturn CVPixelBufferCreateWithBytes(
    CFAllocatorRef allocator, size_t width, size_t height, OSType pixelFormat,
    void *baseAddress, size_t bytesPerRow, CVPixelBufferReleaseBytesCallback releaseBytes,
    void *context, CFDictionaryRef attributes, CVPixelBufferRef *buffer);
CF_EXPORT CVReturn CVPixelBufferLockBaseAddress(CVPixelBufferRef buffer, CVPixelBufferLockFlags flags);
CF_EXPORT CVReturn CVPixelBufferUnlockBaseAddress(CVPixelBufferRef buffer, CVPixelBufferLockFlags flags);
CF_EXPORT size_t CVPixelBufferGetWidth(CVPixelBufferRef buffer);
CF_EXPORT size_t CVPixelBufferGetHeight(CVPixelBufferRef buffer);
CF_EXPORT size_t CVPixelBufferGetWidthOfPlane(CVPixelBufferRef buffer, size_t plane);
CF_EXPORT size_t CVPixelBufferGetHeightOfPlane(CVPixelBufferRef buffer, size_t plane);
CF_EXPORT size_t CVPixelBufferGetBytesPerRow(CVPixelBufferRef buffer);
CF_EXPORT size_t CVPixelBufferGetBytesPerRowOfPlane(CVPixelBufferRef buffer, size_t plane);
CF_EXPORT void *CVPixelBufferGetBaseAddress(CVPixelBufferRef buffer);
CF_EXPORT void *CVPixelBufferGetBaseAddressOfPlane(CVPixelBufferRef buffer, size_t plane);
CF_EXPORT OSType CVPixelBufferGetPixelFormatType(CVPixelBufferRef buffer);
CF_EXPORT Boolean CVPixelBufferIsPlanar(CVPixelBufferRef buffer);
CF_EXTERN_C_END
