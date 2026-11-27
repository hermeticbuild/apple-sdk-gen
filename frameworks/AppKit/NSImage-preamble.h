#pragma once

#import <AppKit/AppKit.h>

#ifdef __OBJC__

/* See provenance.md for the public sources of these supporting types. */
@class NSCoder, NSImageSymbolConfiguration, NSLocale, NSPasteboard;
@protocol NSImageDelegate;

#if !__has_include(<CoreGraphics/CGGeometry.h>) || !__has_include(<CoreGraphics/CoreGraphics.h>)
typedef struct CGImage *CGImageRef;
#endif

typedef NSString *NSImageName;

typedef NS_ENUM(NSInteger, NSImageResizingMode) {
    NSImageResizingModeStretch = 0,
    NSImageResizingModeTile = 1,
};

typedef NS_ENUM(NSUInteger, NSImageCacheMode) {
    NSImageCacheDefault = 0,
    NSImageCacheAlways = 1,
    NSImageCacheBySize = 2,
    NSImageCacheNever = 3,
};

typedef NS_ENUM(NSUInteger, NSTIFFCompression) {
    NSTIFFCompressionNone = 1,
    NSTIFFCompressionCCITTFAX3 = 3,
    NSTIFFCompressionCCITTFAX4 = 4,
    NSTIFFCompressionLZW = 5,
    NSTIFFCompressionJPEG = 6,
    NSTIFFCompressionNEXT = 32766,
    NSTIFFCompressionPackBits = 32773,
    NSTIFFCompressionOldJPEG = 32865,
};
