#pragma once

#import <Foundation/Foundation.h>

#if __has_include(<CoreGraphics/CGGeometry.h>) && __has_include(<CoreGraphics/CoreGraphics.h>)
#import <CoreGraphics/CoreGraphics.h>
#endif

#ifdef __OBJC__
#import <QuartzCore/CALayer.h>
@class NSApplication, NSEvent, NSGraphicsContext, NSImageRep, NSScreen, NSWindow;

typedef NSInteger NSApplicationActivationPolicy;
typedef NSInteger NSLineBreakMode;
typedef NSUInteger NSBackingStoreType;
typedef NSUInteger NSBitmapFormat;
typedef NSUInteger NSCompositingOperation;
typedef NSUInteger NSEventMask;
typedef NSUInteger NSEventModifierFlags;
typedef short NSEventSubtype;
typedef NSUInteger NSEventType;
typedef NSUInteger NSWindowCollectionBehavior;
typedef NSUInteger NSWindowStyleMask;

enum {
    NSApplicationActivationPolicyRegular = 0,
    NSApplicationActivationPolicyAccessory = 1,
    NSApplicationActivationPolicyProhibited = 2,
    NSBackingStoreBuffered = 2,
    NSCompositeSourceOver = 2,
    NSLineBreakByTruncatingTail = 4,
    NSViewWidthSizable = 2,
    NSTitledWindowMask = 1u << 0,
    NSMiniaturizableWindowMask = 1u << 2,
    NSResizableWindowMask = 1u << 3,
    NSFullScreenWindowMask = 1u << 14,
    NSWindowCollectionBehaviorFullScreenPrimary = 1u << 7,
};

enum {
    NSLeftMouseDown = 1,
    NSLeftMouseUp = 2,
    NSRightMouseDown = 3,
    NSRightMouseUp = 4,
    NSMouseMoved = 5,
    NSLeftMouseDragged = 6,
    NSRightMouseDragged = 7,
    NSKeyDown = 10,
    NSEventTypeApplicationDefined = 15,
    NSEventSubtypeApplicationActivated = 1,
    NSEventTypeScrollWheel = 22,
    NSOtherMouseDown = 25,
    NSOtherMouseUp = 26,
    NSOtherMouseDragged = 27,
    NSShiftKeyMask = 1u << 17,
    NSControlKeyMask = 1u << 18,
    NSAlternateKeyMask = 1u << 19,
};
static const NSEventMask NSAnyEventMask = ~(NSEventMask)0;

CF_EXTERN_C_BEGIN
CF_EXPORT NSApplication *NSApp;
CF_EXPORT const double NSAppKitVersionNumber;
CF_EXPORT NSString *const NSDeviceRGBColorSpace;
CF_EXPORT NSString *const NSPasteboardTypeHTML;
CF_EXPORT NSString *const NSPasteboardTypeString;
CF_EXPORT NSString *const NSPasteboardTypeTIFF;
CF_EXPORT NSString *const NSPasteboardURLReadingFileURLsOnlyKey;
CF_EXTERN_C_END

#if __has_include(<CoreGraphics/CGGeometry.h>) && __has_include(<CoreGraphics/CoreGraphics.h>)
#define NSStatusWindowLevel (CGWindowLevelForKey(kCGStatusWindowLevelKey))
#endif

@interface NSColor : NSObject
+ (NSColor *)colorWithSRGBRed:(CGFloat)red green:(CGFloat)green
                         blue:(CGFloat)blue alpha:(CGFloat)alpha;
@property (readonly) CGFloat redComponent;
@property (readonly) CGFloat greenComponent;
@property (readonly) CGFloat blueComponent;
@property (readonly) CGFloat alphaComponent;
@end

@interface NSResponder : NSObject
- (void)keyDown:(NSEvent *)event;
@end

@protocol NSApplicationDelegate <NSObject>
@optional
- (void)applicationDidFinishLaunching:(NSNotification *)notification;
@end

@interface NSApplication : NSResponder
+ (NSApplication *)sharedApplication;
@property (weak) id<NSApplicationDelegate> delegate;
- (void)run;
- (void)stop:(id)sender;
- (void)postEvent:(NSEvent *)event atStart:(BOOL)atStart;
- (NSApplicationActivationPolicy)activationPolicy;
- (BOOL)setActivationPolicy:(NSApplicationActivationPolicy)policy;
- (void)activateIgnoringOtherApps:(BOOL)flag;
- (NSEvent *)nextEventMatchingMask:(NSEventMask)mask untilDate:(NSDate *)expiration
                           inMode:(NSRunLoopMode)mode dequeue:(BOOL)dequeue;
- (void)sendEvent:(NSEvent *)event;
- (void)updateWindows;
@end

@interface NSEvent : NSObject
+ (NSPoint)mouseLocation;
+ (NSEvent *)otherEventWithType:(NSEventType)type location:(NSPoint)location
                 modifierFlags:(NSEventModifierFlags)flags timestamp:(NSTimeInterval)timestamp
                  windowNumber:(NSInteger)number context:(NSGraphicsContext *)context
                       subtype:(short)subtype data1:(NSInteger)data1 data2:(NSInteger)data2;
@property (readonly) NSString *characters;
@property (readonly) NSEventType type;
@property (readonly) NSEventSubtype subtype;
@property (readonly) NSEventModifierFlags modifierFlags;
@property (readonly) BOOL hasPreciseScrollingDeltas;
@property (readonly) CGFloat scrollingDeltaX;
@property (readonly) CGFloat scrollingDeltaY;
@end

@interface NSGraphicsContext : NSObject
@end

@interface NSScreen : NSObject
+ (NSScreen *)mainScreen;
@property (readonly) NSRect frame;
@property (readonly) NSRect visibleFrame;
@end

@interface NSView : NSResponder
- (instancetype)initWithFrame:(NSRect)frame;
- (void)addSubview:(NSView *)view;
- (NSSize)convertSizeFromBacking:(NSSize)size;
- (void)drawRect:(NSRect)dirtyRect;
- (void)setFrameSize:(NSSize)size;
- (void)setNeedsDisplayInRect:(NSRect)rect;
@property NSRect frame;
@property BOOL needsDisplay;
@property NSUInteger autoresizingMask;
@property BOOL wantsLayer;
@property (readonly) CALayer *layer;
@property (readonly) NSWindow *window;
@end

@interface NSCell : NSObject
@property NSLineBreakMode lineBreakMode;
@end

@interface NSControl : NSView
@property BOOL continuous;
@property int intValue;
@property SEL action;
@property (assign) id target;
@property (copy) NSString *stringValue;
@property (strong) __kindof NSCell *cell;
@end

@interface NSSlider : NSControl
@property double minValue;
@property double maxValue;
@end

@interface NSTextField : NSControl
@property (getter=isEditable) BOOL editable;
@property (getter=isSelectable) BOOL selectable;
@property (getter=isBezeled) BOOL bezeled;
@property (getter=isBordered) BOOL bordered;
@property BOOL drawsBackground;
@end

@interface NSImage : NSObject
- (instancetype)initWithSize:(NSSize)size;
- (instancetype)initWithData:(NSData *)data;
- (instancetype)initByReferencingFile:(NSString *)fileName;
@property NSSize size;
- (void)addRepresentation:(NSImageRep *)representation;
- (void)drawInRect:(NSRect)destination fromRect:(NSRect)source
        operation:(NSCompositingOperation)operation fraction:(CGFloat)fraction;
@end

@interface NSImageRep : NSObject
@end

@interface NSBitmapImageRep : NSImageRep
- (instancetype)initWithBitmapDataPlanes:(unsigned char **)planes
                              pixelsWide:(NSInteger)width pixelsHigh:(NSInteger)height
                           bitsPerSample:(NSInteger)bitsPerSample samplesPerPixel:(NSInteger)samplesPerPixel
                                hasAlpha:(BOOL)alpha isPlanar:(BOOL)planar colorSpaceName:(NSString *)colorSpace
                             bitmapFormat:(NSBitmapFormat)format bytesPerRow:(NSInteger)bytesPerRow
                             bitsPerPixel:(NSInteger)bitsPerPixel;
- (instancetype)initWithBitmapDataPlanes:(unsigned char **)planes
                              pixelsWide:(NSInteger)width pixelsHigh:(NSInteger)height
                           bitsPerSample:(NSInteger)bitsPerSample samplesPerPixel:(NSInteger)samplesPerPixel
                                hasAlpha:(BOOL)alpha isPlanar:(BOOL)planar colorSpaceName:(NSString *)colorSpace
                             bytesPerRow:(NSInteger)bytesPerRow bitsPerPixel:(NSInteger)bitsPerPixel;
@property (readonly) unsigned char *bitmapData;
@property (readonly) NSInteger bytesPerRow;
@end

@interface NSWindow : NSResponder
+ (CGFloat)minFrameWidthWithTitle:(NSString *)title styleMask:(NSWindowStyleMask)styleMask;
- (instancetype)initWithContentRect:(NSRect)rect styleMask:(NSWindowStyleMask)styleMask
                             backing:(NSBackingStoreType)backing defer:(BOOL)defer screen:(NSScreen *)screen;
- (void)close;
- (NSRect)contentRectForFrameRect:(NSRect)frame;
- (NSRect)convertRectToScreen:(NSRect)rect;
- (NSPoint)convertBaseToScreen:(NSPoint)point;
- (NSPoint)convertScreenToBase:(NSPoint)point;
- (void)makeKeyAndOrderFront:(id)sender;
- (void)setContentSize:(NSSize)size;
- (void)setFrame:(NSRect)frame display:(BOOL)display;
- (void)setFrameTopLeftPoint:(NSPoint)point;
- (void)toggleFullScreen:(id)sender;
- (void)useOptimizedDrawing:(BOOL)flag;
@property BOOL acceptsMouseMovedEvents;
@property BOOL hasShadow;
@property NSWindowCollectionBehavior collectionBehavior;
@property (strong) NSView *contentView;
@property (readonly) NSRect frame;
@property NSInteger level;
@property (readonly) NSScreen *screen;
@property NSWindowStyleMask styleMask;
@property (copy) NSString *title;
@property (readonly, getter=isVisible) BOOL visible;
@end
#endif
