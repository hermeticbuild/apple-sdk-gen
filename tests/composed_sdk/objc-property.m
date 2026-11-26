#import <Foundation/Foundation.h>

@interface Parent : NSObject
- (NSString *)message;
@end

@implementation Parent
- (NSString *)message {
    return @"parent";
}
@end

@interface Child : Parent
@property (retain) NSString *name;
@end

@implementation Child
- (NSString *)message {
    return [[super message] stringByAppendingString:self.name];
}
@end

int main(void) {
    @autoreleasepool {
        Child *child = [Child new];
        child.name = @"-child";
        BOOL matches = [[child message] isEqualToString:@"parent-child"];
        child.name = nil;
        [child release];
        return !matches;
    }
}
