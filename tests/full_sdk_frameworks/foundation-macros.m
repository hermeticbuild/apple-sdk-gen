#import <Foundation/Foundation.h>

typedef NS_ENUM(NSInteger, ProbeKind) {
    ProbeKindReady = 1,
};

NS_ASSUME_NONNULL_BEGIN
static NSString *name(ProbeKind kind) {
    return kind == ProbeKindReady ? @"ready" : @"unknown";
}
NS_ASSUME_NONNULL_END

int main(void) {
    @autoreleasepool {
        return ![name(ProbeKindReady) isEqualToString:@"ready"];
    }
}
