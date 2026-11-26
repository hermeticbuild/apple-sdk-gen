#pragma once

#ifdef __OBJC__
#import <Foundation/Foundation.h>

typedef NS_ENUM(NSUInteger, NSSearchPathDirectory) {
    NSDocumentDirectory = 9,
    NSDesktopDirectory = 12,
    NSDownloadsDirectory = 15,
    NSMoviesDirectory = 17,
    NSMusicDirectory = 18,
    NSPicturesDirectory = 19,
    NSSharedPublicDirectory = 21,
};

typedef NS_OPTIONS(NSUInteger, NSSearchPathDomainMask) {
    NSUserDomainMask = 1u << 0,
};

CF_EXTERN_C_BEGIN
CF_EXPORT NSArray<NSString *> *NSSearchPathForDirectoriesInDomains(
    NSSearchPathDirectory directory, NSSearchPathDomainMask domains, BOOL expandTilde);
CF_EXTERN_C_END
#endif
