#pragma once

#include <CoreFoundation/CFBase.h>

#if __has_include(<CoreGraphics/CGGeometry.h>)
#include <CoreGraphics/CGGeometry.h>
#else
/* Support the standalone Foundation and Cocoa recipes without a graphics layer. */
typedef double CGFloat;
typedef struct CGPoint { CGFloat x, y; } CGPoint;
typedef struct CGSize { CGFloat width, height; } CGSize;
typedef struct CGRect { CGPoint origin; CGSize size; } CGRect;
#endif

typedef CGPoint NSPoint;
typedef CGSize NSSize;
typedef CGRect NSRect;

CF_EXTERN_C_BEGIN
CF_EXPORT const NSPoint NSZeroPoint;
CF_EXPORT const NSRect NSZeroRect;
CF_EXTERN_C_END

static inline NSPoint NSMakePoint(CGFloat x, CGFloat y) {
    NSPoint point = {x, y};
    return point;
}

static inline NSRect NSMakeRect(CGFloat x, CGFloat y, CGFloat width, CGFloat height) {
    NSRect rect = {{x, y}, {width, height}};
    return rect;
}

static inline CGFloat NSMaxY(NSRect rect) {
    return rect.origin.y + rect.size.height;
}
