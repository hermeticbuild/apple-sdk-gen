#include <math.h>

_Static_assert(_Generic(&__exp10, double (*)(double): 1, default: 0),
               "__exp10 must take and return double");
_Static_assert(_Generic(&__exp10f, float (*)(float): 1, default: 0),
               "__exp10f must take and return float");

int main(void) {
    volatile double exponent = 3.0;
    return __exp10(exponent) != 1000.0 || __exp10f((float)exponent) != 1000.0f;
}
