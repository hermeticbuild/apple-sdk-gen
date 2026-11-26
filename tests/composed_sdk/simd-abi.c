#include <simd/simd.h>

// These checks also run against the Xcode 26.5 arm64 comparison SDK.
#define CHECK_TYPE(type, size, alignment)                                 \
    _Static_assert(sizeof(type) == size, "sizeof(" #type ")");            \
    _Static_assert(_Alignof(type) == alignment, "alignof(" #type ")");     \
    type pass_##type(type value) { return value; }

CHECK_TYPE(vector_double2, 16, 16)
CHECK_TYPE(vector_double3, 32, 16)
CHECK_TYPE(vector_double4, 32, 16)
CHECK_TYPE(vector_float2, 8, 8)
CHECK_TYPE(vector_float3, 16, 16)
CHECK_TYPE(vector_float4, 16, 16)
CHECK_TYPE(vector_int2, 8, 8)
CHECK_TYPE(vector_int4, 16, 16)
CHECK_TYPE(vector_uint2, 8, 8)
CHECK_TYPE(vector_uint3, 16, 16)
CHECK_TYPE(matrix_double4x4, 128, 16)
CHECK_TYPE(matrix_float4x4, 64, 16)
CHECK_TYPE(simd_quatd, 32, 16)
CHECK_TYPE(simd_quatf, 16, 16)

_Static_assert(__builtin_offsetof(matrix_double4x4, columns[1]) == 32, "double column stride");
_Static_assert(__builtin_offsetof(matrix_float4x4, columns[1]) == 16, "float column stride");
_Static_assert(__builtin_offsetof(simd_quatd, vector) == 0, "double quaternion vector");
_Static_assert(__builtin_offsetof(simd_quatf, vector) == 0, "float quaternion vector");

int main(void) {
    vector_float3 value = {1, 2, 3};
    return pass_vector_float3(value).z == 3 ? 0 : 1;
}
