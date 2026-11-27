#include "bootstrap.h"
int probe(int input) {
    return example_function(sizeof(int)) + example_tls + example_aliased() + example_inline(input);
}
