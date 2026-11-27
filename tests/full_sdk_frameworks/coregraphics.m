#import <CoreGraphics/CoreGraphics.h>

int main(void) {
    CGColorRef color = CGColorCreateGenericRGB(1, 0, 0, 1);
    if (!color)
        return 1;
    int failed = CGColorGetAlpha(color) != 1;
    CGColorRelease(color);
    return failed;
}
