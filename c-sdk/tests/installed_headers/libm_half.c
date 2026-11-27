#include <math.h>

#ifdef TEST_HALF_RUNTIME
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static void print_result(const char *name, _Float16 value) {
#if defined(TEST_HALF_WIDEN)
    printf("%s %a\n", name, (double)value);
#else
    uint16_t bits;
    memcpy(&bits, &value, sizeof(bits));
    printf("%s %04x\n", name, (unsigned)bits);
#endif
}

/* Use a volatile function pointer so every observation exercises the dylib. */
#define RUN(name, arguments) do {                                               \
    __typeof__(&name) volatile call = &name;                                      \
    Dl_info info;                                                                \
    if (!dladdr((const void *)call, &info) ||                                     \
        strcmp(info.dli_fname, "/usr/lib/system/libsystem_m.dylib") != 0)         \
        return 1;                                                                \
    print_result(#name, call arguments);                                         \
} while (0)
#else
#define RUN(name, arguments) ((void)0)
#endif

#define CHECK(name, parameters, arguments) do {                                  \
    _Static_assert(__builtin_types_compatible_p(__typeof__(&name),                \
                   _Float16 (*) parameters), "wrong signature for " #name);       \
    RUN(name, arguments);                                                        \
} while (0)

int main(void) {
    CHECK(__ceilf16, (_Float16), (1.25));
    CHECK(__copysignf16, (_Float16, _Float16), (1.0, -2.0));
    CHECK(__fabsf16, (_Float16), (-1.0));
    CHECK(__floorf16, (_Float16), (-1.25));
    CHECK(__fmaf16, (_Float16, _Float16, _Float16), (2.0, 3.0, 4.0));
    CHECK(__fmaxf16, (_Float16, _Float16), (3.0, -3.0));
    CHECK(__fminf16, (_Float16, _Float16), (3.0, -3.0));
    CHECK(__hypotf16, (_Float16, _Float16), (3.0, 4.0));
    CHECK(__nextafterf16, (_Float16, _Float16), (1.0, 2.0));
    CHECK(__rintf16, (_Float16), (1.25));
    CHECK(__roundf16, (_Float16), (-1.5));
    CHECK(__sqrtf16, (_Float16), (4.0));
    CHECK(__truncf16, (_Float16), (-1.75));
    return 0;
}
