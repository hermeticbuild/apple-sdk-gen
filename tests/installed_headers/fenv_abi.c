#include <fenv.h>

_Static_assert(sizeof(fenv_t) == 16, "fenv_t must match the macOS ABI");
