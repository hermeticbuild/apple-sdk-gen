#include <charconv>

int main() {
    const char input[] = "1.25";
    float small = 0;
    double large = 0;
    auto a = std::from_chars(input, input + 4, small);
    auto b = std::from_chars(input, input + 4, large);
    return a.ec != std::errc{} || b.ec != std::errc{} ||
           a.ptr != input + 4 || b.ptr != input + 4 || small != 1.25f || large != 1.25;
}
