#pragma once
#include <stddef.h>

#define FIELD_AT(type, field, offset) \
    _Static_assert(offsetof(type, field) == (offset), #type "." #field)

#define FUNCTION_TYPE(function, result, ...) \
    _Static_assert(__builtin_types_compatible_p(__typeof__(&(function)), \
                   result (*)(__VA_ARGS__)), #function " signature"); \
    static __typeof__(&(function)) const reference_##function __attribute__((used)) = &(function)
