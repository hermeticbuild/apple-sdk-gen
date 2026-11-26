#pragma once

#include <CoreFoundation/CFBase.h>
#include <CoreVideo/CoreVideo.h>

typedef int64_t CMTimeValue;
typedef int32_t CMTimeScale;
typedef uint32_t CMTimeFlags;
typedef int64_t CMTimeEpoch;

typedef struct {
    CMTimeValue value;
    CMTimeScale timescale;
    CMTimeFlags flags;
    CMTimeEpoch epoch;
} CMTime;

typedef struct {
    CMTime start;
    CMTime duration;
} CMTimeRange;

typedef struct {
    int32_t width;
    int32_t height;
} CMVideoDimensions;

typedef const struct opaqueCMFormatDescription *CMFormatDescriptionRef;
typedef CMFormatDescriptionRef CMVideoFormatDescriptionRef;
typedef struct opaqueCMSampleBuffer *CMSampleBufferRef;

CF_EXTERN_C_BEGIN
CF_EXPORT const CMTime kCMTimeZero;
CF_EXPORT const CMTime kCMTimePositiveInfinity;
CF_EXPORT CMTime CMTimeMake(CMTimeValue value, CMTimeScale timescale);
CF_EXPORT CMTime CMTimeMultiply(CMTime time, int32_t multiplier);
CF_EXPORT CMTimeRange CMTimeRangeMake(CMTime start, CMTime duration);
CF_EXPORT CMVideoDimensions CMVideoFormatDescriptionGetDimensions(CMVideoFormatDescriptionRef description);
CF_EXPORT CVImageBufferRef CMSampleBufferGetImageBuffer(CMSampleBufferRef buffer);
CF_EXPORT CMTime CMSampleBufferGetOutputPresentationTimeStamp(CMSampleBufferRef buffer);
CF_EXTERN_C_END
