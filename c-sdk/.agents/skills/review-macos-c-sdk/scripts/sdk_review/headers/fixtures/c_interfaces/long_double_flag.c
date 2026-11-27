#include <ConditionalMacros.h>

_Static_assert(TYPE_LONGDOUBLE_IS_DOUBLE == (sizeof(long double) == sizeof(double)),
               "long double flag");
