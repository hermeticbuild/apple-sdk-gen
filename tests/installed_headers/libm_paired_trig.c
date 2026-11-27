#include <math.h>

#if __ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__ >= 1090
typedef char float_pair_layout[
    sizeof(struct __float2) == 2 * sizeof(float) &&
    __builtin_offsetof(struct __float2, __sinval) == 0 &&
    __builtin_offsetof(struct __float2, __cosval) == sizeof(float) ? 1 : -1];
typedef char double_pair_layout[
    sizeof(struct __double2) == 2 * sizeof(double) &&
    __builtin_offsetof(struct __double2, __sinval) == 0 &&
    __builtin_offsetof(struct __double2, __cosval) == sizeof(double) ? 1 : -1];
#endif

#ifdef TAKE_PAIRED_TRIG_ADDRESSES
void (*volatile paired_double)(double, double *, double *) = __sincos;
void (*volatile paired_float)(float, float *, float *) = __sincosf;
#if __ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__ >= 1090
void (*volatile paired_pi_double)(double, double *, double *) = __sincospi;
void (*volatile paired_pi_float)(float, float *, float *) = __sincospif;
#endif
#else
#define paired_double __sincos
#define paired_float __sincosf
#define paired_pi_double __sincospi
#define paired_pi_float __sincospif
#endif

int main(void)
{
    double ds, dc;
    float fs, fc;

    paired_double(0.5, &ds, &dc);
    paired_float(0.5f, &fs, &fc);
    if (!(__builtin_fabs(ds - 0.479425538604203) < 1e-12 &&
          __builtin_fabs(dc - 0.877582561890373) < 1e-12 &&
          __builtin_fabsf(fs - 0.47942554f) < 1e-6f &&
          __builtin_fabsf(fc - 0.87758256f) < 1e-6f))
        return 1;

    paired_double(-0.0, &ds, &dc);
    paired_float(-0.0f, &fs, &fc);
    if (ds != 0.0 || !__builtin_signbit(ds) || dc != 1.0 ||
        fs != 0.0f || !__builtin_signbit(fs) || fc != 1.0f)
        return 2;

    paired_double(0.0, &ds, &ds);
    paired_float(0.0f, &fs, &fs);
    if (ds != 1.0 || fs != 1.0f)
        return 3;

#if __ENVIRONMENT_MAC_OS_X_VERSION_MIN_REQUIRED__ >= 1090
    paired_pi_double(0.5, &ds, &dc);
    paired_pi_float(0.5f, &fs, &fc);
    if (ds != 1.0 || dc != 0.0 || fs != 1.0f || fc != 0.0f)
        return 4;

    paired_pi_double(-0.0, &ds, &dc);
    paired_pi_float(-0.0f, &fs, &fc);
    if (ds != 0.0 || !__builtin_signbit(ds) || dc != 1.0 ||
        fs != 0.0f || !__builtin_signbit(fs) || fc != 1.0f)
        return 5;
#endif

    return 0;
}
