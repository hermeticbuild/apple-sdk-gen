#include <complex.h>

#if defined(__cplusplus) || ((!defined(__STDC_VERSION__) || __STDC_VERSION__ < 201112L) && \
                             __DARWIN_C_LEVEL < __DARWIN_C_FULL)
#if defined(CMPLX) || defined(CMPLXF) || defined(CMPLXL)
#error "complex constructors exposed outside C11 or full Darwin C"
#endif
#elif !defined(__STDC_VERSION__) || __STDC_VERSION__ < 201112L
/* Full Darwin C exposes constructors even without C11 type generics. */
static double complex darwin_double = CMPLX(1.0, 2.0);
static float complex darwin_float = CMPLXF(1.0f, 2.0f);
static long double complex darwin_long = CMPLXL(1.0L, 2.0L);
int main(void) {
    return creal(darwin_double) != 1.0 || cimagf(darwin_float) != 2.0f ||
           cimagl(darwin_long) != 2.0L;
}
#else
#include <math.h>

_Static_assert(_Generic(CMPLX(4.0f, 3), double complex: 1, default: 0),
               "CMPLX must yield double complex");
_Static_assert(_Generic(CMPLXF(4.0, 3), float complex: 1, default: 0),
               "CMPLXF must yield float complex");
_Static_assert(_Generic(CMPLXL(4.0f, 3), long double complex: 1, default: 0),
               "CMPLXL must yield long double complex");

static double complex static_double = CMPLX(-0.0, 0.0);
static _Thread_local float complex thread_float = CMPLXF(0.0f, -0.0f);
static long double complex static_long_double = CMPLXL(-0.0L, -0.0L);
static float complex infinite_imaginary = CMPLXF(1.0f, INFINITY);

int main(void) {
    if (creal(static_double) != 0.0 || !signbit(creal(static_double)) ||
        cimag(static_double) != 0.0 || signbit(cimag(static_double))) {
        return 1;
    }
    if (crealf(thread_float) != 0.0f || signbit(crealf(thread_float)) ||
        cimagf(thread_float) != 0.0f || !signbit(cimagf(thread_float))) {
        return 2;
    }
    if (creall(static_long_double) != 0.0L || !signbit(creall(static_long_double)) ||
        cimagl(static_long_double) != 0.0L || !signbit(cimagl(static_long_double))) {
        return 3;
    }
    if (crealf(infinite_imaginary) != 1.0f || cimagf(infinite_imaginary) != INFINITY) {
        return 4;
    }

    int real = 0;
    int imaginary = 10;
    double complex d = CMPLX(real++, imaginary--);
    float complex f = CMPLXF(real++, imaginary--);
    long double complex l = CMPLXL(real++, imaginary--);
    if (real != 3 || imaginary != 7 || creal(d) != 0.0 || cimag(d) != 10.0 ||
        crealf(f) != 1.0f || cimagf(f) != 9.0f || creall(l) != 2.0L || cimagl(l) != 8.0L) {
        return 5;
    }
    return 0;
}
#endif
