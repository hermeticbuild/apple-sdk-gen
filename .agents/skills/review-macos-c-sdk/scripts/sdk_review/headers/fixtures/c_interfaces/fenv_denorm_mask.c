#include <fenv.h>

#ifdef __arm64__
_Static_assert(FE_FLUSHTOZERO == 0x80, "arm64 input-denormal flag");
_Static_assert(FE_ALL_EXCEPT == 159, "arm64 mask");
#else
_Static_assert(FE_DENORMALOPERAND == 0x02, "Intel denormal-operand flag");
_Static_assert(FE_ALL_EXCEPT == 63, "Intel mask");
#endif
