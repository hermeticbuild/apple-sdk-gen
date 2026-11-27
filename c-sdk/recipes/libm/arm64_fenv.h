/*
 * arm64 C floating-point environment declarations.
 *
 * Derived from Libm/Source/ARM/fenv.h (C API and FE_* names) and
 * xnu/osfmk/arm64/proc_reg.h (FPSR exception and FPCR rounding bits).
 * The two-register, 16-byte object layout was checked against macOS
 * libSystem behavior, without reading an SDK header.
 */
#ifndef _APPLE_OSS_C_ARM64_FENV_H_
#define _APPLE_OSS_C_ARM64_FENV_H_

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    unsigned long long __fpsr;
    unsigned long long __fpcr;
} fenv_t;

typedef unsigned short fexcept_t;

#define FE_INVALID    (1 << 0) /* XNU FPSR_IOC */
#define FE_DIVBYZERO  (1 << 1) /* XNU FPSR_DZC */
#define FE_OVERFLOW   (1 << 2) /* XNU FPSR_OFC */
#define FE_UNDERFLOW  (1 << 3) /* XNU FPSR_UFC */
#define FE_INEXACT    (1 << 4) /* XNU FPSR_IXC */
#define FE_FLUSHTOZERO (1 << 7) /* XNU FPSR_IDC */
#define FE_ALL_EXCEPT (FE_INVALID | FE_DIVBYZERO | FE_OVERFLOW | FE_UNDERFLOW | \
                       FE_INEXACT | FE_FLUSHTOZERO)

#define FE_TONEAREST  0
#define FE_UPWARD     (1 << 22) /* XNU FPCR_RMODE */
#define FE_DOWNWARD   (2 << 22)
#define FE_TOWARDZERO (3 << 22)

extern const fenv_t _FE_DFL_ENV;
#define FE_DFL_ENV (&_FE_DFL_ENV)

int feclearexcept(int);
int fegetexceptflag(fexcept_t *, int);
int feraiseexcept(int);
int fesetexceptflag(const fexcept_t *, int);
int fetestexcept(int);
int fegetround(void);
int fesetround(int);
int fegetenv(fenv_t *);
int feholdexcept(fenv_t *);
int fesetenv(const fenv_t *);
int feupdateenv(const fenv_t *);

#ifdef __cplusplus
}
#endif
#endif
