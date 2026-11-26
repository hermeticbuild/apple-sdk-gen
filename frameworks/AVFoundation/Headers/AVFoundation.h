#pragma once

#include <CoreMedia/CoreMedia.h>

#ifdef __OBJC__
#import <CoreGraphics/CoreGraphics.h>
#import <Foundation/Foundation.h>
#include <dispatch/dispatch.h>

typedef NSString *AVMediaType;
typedef NSString *AVFileType;
typedef NSString *AVVideoCodecType;
typedef NSString *AVCaptureSessionPreset;

typedef NSInteger AVAuthorizationStatus;
typedef NSInteger AVAssetReaderStatus;
typedef NSInteger AVAssetWriterStatus;

enum {
    AVAuthorizationStatusNotDetermined = 0,
    AVAuthorizationStatusRestricted = 1,
    AVAuthorizationStatusDenied = 2,
    AVAuthorizationStatusAuthorized = 3,
};
enum {
    AVAssetReaderStatusUnknown = 0,
    AVAssetReaderStatusReading = 1,
    AVAssetReaderStatusCompleted = 2,
    AVAssetReaderStatusFailed = 3,
    AVAssetReaderStatusCancelled = 4,
};
enum {
    AVAssetWriterStatusUnknown = 0,
    AVAssetWriterStatusWriting = 1,
    AVAssetWriterStatusCompleted = 2,
    AVAssetWriterStatusFailed = 3,
    AVAssetWriterStatusCancelled = 4,
};

CF_EXTERN_C_BEGIN
CF_EXPORT AVMediaType const AVMediaTypeVideo;
CF_EXPORT AVMediaType const AVMediaTypeMuxed;
CF_EXPORT AVFileType const AVFileTypeQuickTimeMovie;
CF_EXPORT AVFileType const AVFileTypeMPEG4;
CF_EXPORT AVFileType const AVFileTypeAppleM4V;
CF_EXPORT AVVideoCodecType const AVVideoCodecTypeH264;
CF_EXPORT AVVideoCodecType const AVVideoCodecTypeJPEG;
CF_EXPORT AVVideoCodecType const AVVideoCodecTypeHEVC;
CF_EXPORT AVCaptureSessionPreset const AVCaptureSessionPresetMedium;
CF_EXPORT NSString *const AVVideoCodecKey;
CF_EXPORT NSString *const AVVideoWidthKey;
CF_EXPORT NSString *const AVVideoHeightKey;
CF_EXTERN_C_END

@class AVAssetTrack, AVCaptureConnection, AVCaptureOutput;

@interface AVFrameRateRange : NSObject
@property (readonly) double maxFrameRate;
@property (readonly) CMTime minFrameDuration;
@end

@interface AVCaptureDeviceFormat : NSObject
@property (readonly) CMFormatDescriptionRef formatDescription;
@property (readonly) NSArray<AVFrameRateRange *> *videoSupportedFrameRateRanges;
@end

@interface AVCaptureDevice : NSObject
+ (AVAuthorizationStatus)authorizationStatusForMediaType:(AVMediaType)mediaType;
+ (void)requestAccessForMediaType:(AVMediaType)mediaType completionHandler:(void (^)(BOOL))handler;
+ (NSArray<AVCaptureDevice *> *)devicesWithMediaType:(AVMediaType)mediaType;
- (BOOL)lockForConfiguration:(NSError **)error;
- (void)unlockForConfiguration;
@property (readonly) NSString *uniqueID;
@property (readonly) AVCaptureDeviceFormat *activeFormat;
@property CMTime activeVideoMaxFrameDuration;
@property CMTime activeVideoMinFrameDuration;
@end

@interface AVCaptureInput : NSObject
@end

@interface AVCaptureDeviceInput : AVCaptureInput
- (instancetype)initWithDevice:(AVCaptureDevice *)device error:(NSError **)error;
@end

@interface AVCaptureOutput : NSObject
@end

@protocol AVCaptureVideoDataOutputSampleBufferDelegate <NSObject>
@optional
- (void)captureOutput:(AVCaptureOutput *)output didOutputSampleBuffer:(CMSampleBufferRef)buffer
       fromConnection:(AVCaptureConnection *)connection;
@end

@interface AVCaptureVideoDataOutput : AVCaptureOutput
- (void)setSampleBufferDelegate:(id<AVCaptureVideoDataOutputSampleBufferDelegate>)delegate
                           queue:(dispatch_queue_t)queue;
@property (copy) NSDictionary<NSString *, id> *videoSettings;
@property BOOL alwaysDiscardsLateVideoFrames;
@end

@interface AVCaptureSession : NSObject
- (void)addInput:(AVCaptureInput *)input;
- (void)addOutput:(AVCaptureOutput *)output;
- (void)startRunning;
- (void)stopRunning;
@property (copy) AVCaptureSessionPreset sessionPreset;
@end

@interface AVAsset : NSObject
+ (AVAsset *)assetWithURL:(NSURL *)URL;
- (NSArray<AVAssetTrack *> *)tracksWithMediaType:(AVMediaType)mediaType;
@property (readonly) CMTime duration;
@end

@interface AVAssetTrack : NSObject
@property (readonly) float nominalFrameRate;
@property (readonly) CGSize naturalSize;
@property (readonly) CMTime minFrameDuration;
@property (readonly) CGAffineTransform preferredTransform;
@end

@interface AVAssetReaderOutput : NSObject
- (CMSampleBufferRef)copyNextSampleBuffer;
@end

@interface AVAssetReaderTrackOutput : AVAssetReaderOutput
+ (instancetype)assetReaderTrackOutputWithTrack:(AVAssetTrack *)track
                                  outputSettings:(NSDictionary<NSString *, id> *)settings;
@end

@interface AVAssetReader : NSObject
+ (instancetype)assetReaderWithAsset:(AVAsset *)asset error:(NSError **)error;
- (void)addOutput:(AVAssetReaderOutput *)output;
- (BOOL)startReading;
- (void)cancelReading;
@property CMTimeRange timeRange;
@property (readonly) AVAssetReaderStatus status;
@end

@interface AVAssetWriterInput : NSObject
+ (instancetype)assetWriterInputWithMediaType:(AVMediaType)mediaType
                                outputSettings:(NSDictionary<NSString *, id> *)settings;
- (void)markAsFinished;
@property (readonly, getter=isReadyForMoreMediaData) BOOL readyForMoreMediaData;
@end

@interface AVAssetWriterInputPixelBufferAdaptor : NSObject
- (instancetype)initWithAssetWriterInput:(AVAssetWriterInput *)input
                 sourcePixelBufferAttributes:(NSDictionary<NSString *, id> *)attributes;
- (BOOL)appendPixelBuffer:(CVPixelBufferRef)buffer withPresentationTime:(CMTime)time;
@end

@interface AVAssetWriter : NSObject
- (instancetype)initWithURL:(NSURL *)URL fileType:(AVFileType)fileType error:(NSError **)error;
- (void)addInput:(AVAssetWriterInput *)input;
- (BOOL)startWriting;
- (BOOL)finishWriting;
- (void)startSessionAtSourceTime:(CMTime)time;
@property (readonly) AVAssetWriterStatus status;
@property (readonly) NSError *error;
@end
#endif
