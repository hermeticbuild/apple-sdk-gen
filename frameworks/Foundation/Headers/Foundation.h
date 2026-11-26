#pragma once

#include <CoreFoundation/CFBase.h>
#include <objc/objc.h>
#include <Foundation/NSGeometry.h>

#ifndef NS_ENUM
#define NS_ENUM(...) CF_ENUM(__VA_ARGS__)
#endif
#ifndef NS_OPTIONS
#define NS_OPTIONS(type, name) CF_OPTIONS(type, name)
#endif
#ifndef NS_ASSUME_NONNULL_BEGIN
#define NS_ASSUME_NONNULL_BEGIN CF_ASSUME_NONNULL_BEGIN
#endif
#ifndef NS_ASSUME_NONNULL_END
#define NS_ASSUME_NONNULL_END CF_ASSUME_NONNULL_END
#endif

/* The trial targets macOS LP64. The ranges follow Apple's documented
 * NSUInteger location/length contract and are validated by value. */
typedef long NSInteger;
typedef unsigned long NSUInteger;
typedef double NSTimeInterval;
typedef struct _NSRange {
    NSUInteger location;
    NSUInteger length;
} NSRange;

static inline NSRange NSMakeRange(NSUInteger location, NSUInteger length) {
    NSRange result = {location, length};
    return result;
}

static inline NSUInteger NSMaxRange(NSRange range) {
    return range.location + range.length;
}

#ifdef __OBJC__
#import <objc/NSObject.h>

@class NSString;
@class NSData;
@class NSImage;
@class NSNotification;
@class NSUserNotificationCenter;
@protocol NSCopying;
typedef NSString *NSErrorDomain;
typedef NSString *NSErrorUserInfoKey;
typedef NSString *NSNotificationName;
typedef NSString *NSRunLoopMode;
typedef NSUInteger NSStringEncoding;
typedef NSInteger NSComparisonResult;
typedef unsigned short unichar;
typedef NSComparisonResult (^NSComparator)(id left, id right);

enum {
    NSOrderedAscending = -1,
    NSOrderedSame = 0,
    NSOrderedDescending = 1,
    NSASCIIStringEncoding = 1,
    NSUTF8StringEncoding = 4,
};

typedef struct {
    unsigned long state;
    id __unsafe_unretained *itemsPtr;
    unsigned long *mutationsPtr;
    unsigned long extra[5];
} NSFastEnumerationState;

@protocol NSFastEnumeration
- (NSUInteger)countByEnumeratingWithState:(NSFastEnumerationState *)state
                                 objects:(id __unsafe_unretained [])objects
                                   count:(NSUInteger)count;
@end

@interface NSString : NSObject
- (instancetype)initWithUTF8String:(const char *)bytes;
- (instancetype)initWithData:(NSData *)data encoding:(NSStringEncoding)encoding;
+ (instancetype)stringWithUTF8String:(const char *)bytes;
+ (instancetype)stringWithString:(NSString *)string;
+ (instancetype)stringWithFormat:(NSString *)format, ...;
- (NSString *)stringByAppendingString:(NSString *)string;
- (NSRange)rangeOfString:(NSString *)string;
- (BOOL)isEqualToString:(NSString *)string;
- (const char *)cStringUsingEncoding:(NSStringEncoding)encoding;
- (unichar)characterAtIndex:(NSUInteger)index;
- (NSComparisonResult)compare:(NSString *)other;
@property (readonly) NSString *stringByExpandingTildeInPath;
@property (readonly) NSString *pathExtension;
@property (readonly) NSString *lowercaseString;
@property (readonly) const char *UTF8String;
@property (readonly) NSUInteger length;
@end

@interface NSArray<__covariant ObjectType> : NSObject <NSFastEnumeration>
+ (instancetype)array;
+ (instancetype)arrayWithObject:(ObjectType)object;
+ (instancetype)arrayWithObjects:(const ObjectType [])objects count:(NSUInteger)count;
- (ObjectType)objectAtIndex:(NSUInteger)index;
- (ObjectType)objectAtIndexedSubscript:(NSUInteger)index;
- (NSArray<ObjectType> *)arrayByAddingObjectsFromArray:(NSArray<ObjectType> *)objects;
- (NSArray<ObjectType> *)sortedArrayUsingComparator:(NSComparator)comparator;
@property (readonly) NSUInteger count;
@property (readonly) ObjectType firstObject;
@property (readonly) ObjectType lastObject;
@end

@interface NSMutableArray<ObjectType> : NSArray<ObjectType>
+ (instancetype)arrayWithCapacity:(NSUInteger)capacity;
- (void)addObject:(ObjectType)object;
@end

@interface NSDictionary<__covariant KeyType, __covariant ObjectType> : NSObject <NSFastEnumeration>
+ (instancetype)dictionaryWithDictionary:(NSDictionary<KeyType, ObjectType> *)dictionary;
+ (instancetype)dictionaryWithObjectsAndKeys:(id)firstObject, ...;
+ (instancetype)dictionaryWithObjects:(const ObjectType [])objects
                               forKeys:(const id<NSCopying> [])keys
                                 count:(NSUInteger)count;
@property (readonly) NSUInteger count;
- (ObjectType)objectForKey:(KeyType)key;
- (ObjectType)objectForKeyedSubscript:(KeyType)key;
- (id)valueForKey:(NSString *)key;
- (id)mutableCopy;
@end

@interface NSMutableDictionary<KeyType, ObjectType> : NSDictionary<KeyType, ObjectType>
+ (instancetype)dictionaryWithCapacity:(NSUInteger)capacity;
- (void)removeObjectForKey:(KeyType)key;
- (void)setObject:(ObjectType)object forKey:(KeyType)key;
- (void)setObject:(ObjectType)object forKeyedSubscript:(KeyType)key;
- (void)setValue:(ObjectType)value forKey:(NSString *)key;
@end

@interface NSData : NSObject
+ (instancetype)dataWithBytes:(const void *)bytes length:(NSUInteger)length;
- (instancetype)initWithBytes:(const void *)bytes length:(NSUInteger)length;
@property (readonly) const void *bytes;
@property (readonly) NSUInteger length;
@end

@interface NSError : NSObject
+ (instancetype)errorWithDomain:(NSErrorDomain)domain code:(NSInteger)code
                       userInfo:(NSDictionary<NSString *, id> *)details;
@property (readonly) NSErrorDomain domain;
@property (readonly) NSInteger code;
@property (readonly) NSString *localizedDescription;
@property (readonly) NSDictionary<NSString *, id> *userInfo;
@end

@interface NSURL : NSObject
+ (instancetype)URLWithString:(NSString *)string;
+ (instancetype)fileURLWithPath:(NSString *)path;
@property (readonly) NSString *absoluteString;
@property (readonly) NSString *path;
@property (readonly, getter=isFileURL) BOOL fileURL;
@end

@interface NSValue : NSObject
@end

@interface NSNumber : NSValue
+ (NSNumber *)numberWithBool:(BOOL)value;
+ (NSNumber *)numberWithUnsignedChar:(unsigned char)value;
+ (NSNumber *)numberWithShort:(short)value;
+ (NSNumber *)numberWithUnsignedShort:(unsigned short)value;
+ (NSNumber *)numberWithInt:(int)value;
+ (NSNumber *)numberWithUnsignedInt:(unsigned int)value;
+ (NSNumber *)numberWithLong:(long)value;
+ (NSNumber *)numberWithUnsignedLong:(unsigned long)value;
+ (NSNumber *)numberWithLongLong:(long long)value;
+ (NSNumber *)numberWithUnsignedLongLong:(unsigned long long)value;
+ (NSNumber *)numberWithDouble:(double)value;
@property (readonly) BOOL boolValue;
@property (readonly) unsigned char unsignedCharValue;
@property (readonly) short shortValue;
@property (readonly) unsigned short unsignedShortValue;
@property (readonly) long longValue;
@property (readonly) unsigned long unsignedLongValue;
@property (readonly) long long longLongValue;
@property (readonly) unsigned long long unsignedLongLongValue;
@property (readonly) double doubleValue;
@property (readonly) NSInteger integerValue;
@end

@interface NSDate : NSObject
+ (instancetype)date;
+ (NSDate *)distantPast;
+ (instancetype)dateWithTimeIntervalSinceNow:(NSTimeInterval)interval;
+ (instancetype)dateWithTimeIntervalSince1970:(NSTimeInterval)interval;
@property (readonly) NSTimeInterval timeIntervalSince1970;
@end

@interface NSThread : NSObject
+ (BOOL)isMainThread;
+ (void)sleepForTimeInterval:(NSTimeInterval)interval;
@end

@interface NSRunLoop : NSObject
+ (NSRunLoop *)mainRunLoop;
- (void)runUntilDate:(NSDate *)limit;
@end

@interface NSAutoreleasePool : NSObject
- (void)drain;
@end

@interface NSCondition : NSObject
- (void)lock;
- (void)unlock;
- (void)signal;
- (BOOL)waitUntilDate:(NSDate *)limit;
@end

@interface NSBundle : NSObject
+ (NSBundle *)mainBundle;
+ (instancetype)bundleWithURL:(NSURL *)URL;
@property (readonly, copy) NSString *bundleIdentifier;
@property (readonly, copy) NSString *bundlePath;
- (id)objectForInfoDictionaryKey:(NSString *)key;
@end

@interface NSUserDefaults : NSObject
+ (NSUserDefaults *)standardUserDefaults;
- (id)objectForKey:(NSString *)key;
- (void)setObject:(id)value forKey:(NSString *)key;
- (void)removeObjectForKey:(NSString *)key;
- (BOOL)synchronize;
@end

typedef enum NSUserNotificationActivationType : NSInteger {
    NSUserNotificationActivationTypeContentsClicked = 1,
    NSUserNotificationActivationTypeActionButtonClicked = 2,
} NSUserNotificationActivationType;

@interface NSUserNotification : NSObject
@property (copy) NSString *title;
@property (copy) NSString *informativeText;
@property (copy) NSString *identifier;
@property (copy) NSString *actionButtonTitle;
@property (copy) NSImage *contentImage;
@property (copy) NSDictionary *userInfo;
@property (readonly) NSUserNotificationActivationType activationType;
@end

@protocol NSUserNotificationCenterDelegate <NSObject>
@optional
- (void)userNotificationCenter:(NSUserNotificationCenter *)center
       didActivateNotification:(NSUserNotification *)notification;
@end

@interface NSUserNotificationCenter : NSObject
+ (NSUserNotificationCenter *)defaultUserNotificationCenter;
@property (assign) id<NSUserNotificationCenterDelegate> delegate;
@property (readonly, copy) NSArray<NSUserNotification *> *deliveredNotifications;
- (void)deliverNotification:(NSUserNotification *)notification;
- (void)removeDeliveredNotification:(NSUserNotification *)notification;
@end

CF_EXTERN_C_BEGIN
CF_EXPORT NSRunLoopMode const NSDefaultRunLoopMode;
CF_EXPORT void NSLog(NSString *format, ...);
CF_EXTERN_C_END

#import <Foundation/NSPathUtilities.h>
#endif
