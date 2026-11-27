#include <math.h>

#ifdef __cplusplus
#define CHECK_TYPE(name, type) static_assert(__is_same(decltype(&name), type (*)(type)))
#else
#define CHECK_TYPE(name, type) \
    _Static_assert(_Generic(&name, type (*)(type): 1, default: 0), #name " signature")
#endif

CHECK_TYPE(__cospi, double);
CHECK_TYPE(__cospif, float);
CHECK_TYPE(__tanpi, double);
CHECK_TYPE(__tanpif, float);

int main(void)
{
    volatile double half_turn = 0.5;
    volatile double quarter_turn = -0.25;
    volatile double negative_zero = -0.0;
    double cosine = __cospi(half_turn);
    float cosinef = __cospif((float)half_turn);
    if (cosine != 0.0 || __builtin_signbit(cosine) ||
        cosinef != 0.0f || __builtin_signbit(cosinef))
        return 1;

    if (__tanpi(quarter_turn) != -1.0 || __tanpif((float)quarter_turn) != -1.0f)
        return 2;

    double tangent = __tanpi(negative_zero);
    float tangentf = __tanpif((float)negative_zero);
    return tangent != 0.0 || !__builtin_signbit(tangent) ||
           tangentf != 0.0f || !__builtin_signbit(tangentf);
}
