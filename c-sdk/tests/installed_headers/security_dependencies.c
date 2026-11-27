#include <libDER/DERItem.h>

#if __has_include(<xpc/xpc.h>)
#error "A type-only header must leave the XPC client API unavailable"
#endif

#include <xpc/_xpc_object.h>

_Static_assert(__builtin_types_compatible_p(xpc_object_t, void *), "XPC C object type");
_Static_assert(sizeof(DERItem) == 16, "DER item layout");
