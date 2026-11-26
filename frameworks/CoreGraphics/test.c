#include <stddef.h>

#ifdef GEOMETRY_FIRST
#include <CoreGraphics/CGGeometry.h>
#include <CoreGraphics/CoreGraphics.h>
#else
#include <CoreGraphics/CoreGraphics.h>
#include <CoreGraphics/CGGeometry.h>
#endif

_Static_assert(sizeof(CGFloat) == 8, "CGFloat width");
_Static_assert(sizeof(CGPoint) == 16, "CGPoint size");
_Static_assert(_Alignof(CGPoint) == 8, "CGPoint alignment");
_Static_assert(offsetof(CGPoint, y) == 8, "CGPoint y offset");
