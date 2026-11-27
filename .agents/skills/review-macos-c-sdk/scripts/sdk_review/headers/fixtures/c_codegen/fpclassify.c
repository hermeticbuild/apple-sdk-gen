#include <float.h>
#include <fenv.h>
#include <math.h>
#include <stdint.h>

#if defined(PROBE_FLOAT)
typedef float probe_type;
#define PROBE_TRUE_MIN FLT_TRUE_MIN
#elif defined(PROBE_DOUBLE)
typedef double probe_type;
#define PROBE_TRUE_MIN DBL_TRUE_MIN
#elif defined(PROBE_LONG_DOUBLE)
typedef long double probe_type;
#define PROBE_TRUE_MIN LDBL_TRUE_MIN
#else
#error "Select PROBE_FLOAT, PROBE_DOUBLE, or PROBE_LONG_DOUBLE"
#endif

int main(void) {
    volatile probe_type inputs[] = {-0.0, PROBE_TRUE_MIN, 1.0, INFINITY, NAN};
    const int expected[] = {FP_ZERO, FP_SUBNORMAL, FP_NORMAL, FP_INFINITE, FP_NAN};
    for (unsigned i = 0; i < sizeof(inputs) / sizeof(inputs[0]); ++i) {
        unsigned at = i;
        if (fpclassify(inputs[at++]) != expected[i] || at != i + 1) {
            return i + 1;
        }
    }
#if defined(__arm64__) && (defined(PROBE_DOUBLE) || defined(PROBE_LONG_DOUBLE))
    const uint64_t signaling_nan = UINT64_C(0x7ff0000000000001);
    probe_type nan;
    _Static_assert(sizeof(nan) == sizeof(signaling_nan), "expected Darwin arm64 binary64");
    __builtin_memcpy(&nan, &signaling_nan, sizeof(nan));
    volatile probe_type input = nan;
    if (feclearexcept(FE_ALL_EXCEPT) != 0 || fpclassify(input) != FP_NAN ||
        fetestexcept(FE_INVALID)) {
        return 6;
    }
#endif
    return 0;
}
