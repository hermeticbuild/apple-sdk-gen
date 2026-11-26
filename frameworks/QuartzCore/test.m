#import <QuartzCore/CALayer.h>

int main(void) {
    @autoreleasepool {
        CALayer *layer = [CALayer layer];
        layer.contents = nil;
        return layer == nil || layer.contents != nil;
    }
}
