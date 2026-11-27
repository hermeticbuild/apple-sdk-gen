#include <stddef.h>
extern int example_function(size_t);
extern _Thread_local int example_tls;
extern int example_aliased(void) __asm__("_example_asm_name");
static inline int example_inline(int value) { return value + 1; }
