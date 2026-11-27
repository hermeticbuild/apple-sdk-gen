#define BIND_8_COMPAT
#include <resolv.h>

/* Keep a link reference without sending a query. */
__attribute__((used)) static __typeof__(&res_nsearch) const search_ref = &res_nsearch;

int main(void) {
    struct __res_state state = {0};
    if (res_ninit(&state) != 0)
        return 1;
    res_nclose(&state);
    return 0;
}
