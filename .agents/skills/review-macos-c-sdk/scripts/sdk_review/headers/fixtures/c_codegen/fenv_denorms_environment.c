#include <dlfcn.h>
#include <fenv.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Qualification-only declaration. Never install this fixture as a header. */
#if defined(REVIEW_DERIVED_FENV) && defined(__arm64__)
extern const fenv_t _FE_DFL_DISABLE_DENORMS_ENV;
#define FE_DFL_DISABLE_DENORMS_ENV (&_FE_DFL_DISABLE_DENORMS_ENV)
#endif

#if defined(__arm64__)
#ifndef FE_DFL_DISABLE_DENORMS_ENV
#error missing arm64 extension
#endif
_Static_assert(__builtin_types_compatible_p(__typeof__(FE_DFL_DISABLE_DENORMS_ENV), const fenv_t *), "macro points to const fenv_t");
static const fenv_t * volatile flush = FE_DFL_DISABLE_DENORMS_ENV;

static uint64_t mul_bits(uint64_t x, uint64_t y) {
    double a, b, c;
    uint64_t result;
    memcpy(&a, &x, sizeof a);
    memcpy(&b, &y, sizeof b);
    __asm__ volatile("fmul %d0, %d1, %d2" : "=w"(c) : "w"(a), "w"(b) : "memory");
    memcpy(&result, &c, sizeof result);
    return result;
}

static uint64_t fpcr(void) {
    uint64_t value;
    __asm__ volatile("mrs %0, fpcr" : "=r"(value) :: "memory");
    return value;
}

static uint64_t fpsr(void) {
    uint64_t value;
    __asm__ volatile("mrs %0, fpsr" : "=r"(value) :: "memory");
    return value;
}

int main(void) {
    Dl_info info;
    if (!dladdr(flush, &info) || dlsym(RTLD_DEFAULT, "_FE_DFL_DISABLE_DENORMS_ENV") != flush)
        return 1;
    fprintf(stderr, "%s %s\n", info.dli_fname, info.dli_sname);
    fenv_t saved, selected;
    if (fegetenv(&saved) || fesetround(FE_UPWARD))
        return 2;
    if (fegetenv(&selected)) {
        fesetenv(&saved);
        return 2;
    }
    const uint64_t saved_fpcr = fpcr();
    const uint64_t saved_fpsr = fpsr();
    unsigned failures = 0;
    failures |= !!fesetenv(FE_DFL_ENV);
    const uint64_t smallest = UINT64_C(0x0000000000000001);
    const uint64_t minimum_normal = UINT64_C(0x0010000000000000);
    const uint64_t one = UINT64_C(0x3ff0000000000000);
    const uint64_t half = UINT64_C(0x3fe0000000000000);
    uint64_t default_fpcr = fpcr();
    failures |= mul_bits(smallest, one) != smallest;
    failures |= mul_bits(minimum_normal, half) != minimum_normal / 2;
    failures |= !!fesetenv(flush);
    const uint64_t fz = UINT64_C(1) << 24;
    failures |= (fpcr() ^ default_fpcr) != fz;
    failures |= mul_bits(smallest, one) != 0;
    failures |= mul_bits(minimum_normal, half) != 0;
    failures |= !!fesetenv(&selected);
    failures |= fpcr() != saved_fpcr || fpsr() != saved_fpsr;
    failures |= fegetround() != FE_UPWARD;
    failures |= !!fesetenv(&saved);
    return failures != 0;
}
#else
#ifdef FE_DFL_DISABLE_DENORMS_ENV
#error unexpected generic arm64 extension
#endif
#ifndef FE_DFL_DISABLE_SSE_DENORMS_ENV
#error missing x86 SSE extension
#endif
int main(void) { return !!dlsym(RTLD_DEFAULT, "_FE_DFL_DISABLE_DENORMS_ENV"); }
#endif
