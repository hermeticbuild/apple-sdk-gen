#include <math.h>

_Static_assert(_Generic(&__sinpi, double (*)(double): 1, default: 0),
               "__sinpi must take and return double");
_Static_assert(_Generic(&__sinpif, float (*)(float): 1, default: 0),
               "__sinpif must take and return float");

int main(void) {
    volatile double integer = -1.0;
    volatile double half_integer = 1.5;
    double result = __sinpi(integer);
    float resultf = __sinpif((float)integer);
    return result != 0.0 || !signbit(result) ||
           resultf != 0.0f || !signbit(resultf) ||
           __sinpi(half_integer) != -1.0 || __sinpif((float)half_integer) != -1.0f;
}
