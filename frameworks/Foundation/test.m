#import <Foundation/NSRange.h>
#import <Foundation/NSString.h>
#import <Foundation/Foundation.h>

_Static_assert(sizeof(NSRange) == 2 * sizeof(unsigned long), "NSRange ABI");
_Static_assert(__builtin_offsetof(NSRange, length) == sizeof(unsigned long), "NSRange length offset");
_Static_assert(NSDesktopDirectory == 12 && NSDownloadsDirectory == 15 && NSUserDomainMask == 1,
               "NSPathUtilities ABI");

int main(void) {
    @autoreleasepool {
        NSString *prefix = [NSString stringWithUTF8String:"sdk"];
        NSString *text = [prefix stringByAppendingString:@" probe"];
        NSRange range = [text rangeOfString:@"probe"];
        NSArray<NSString *> *items = [NSArray arrayWithObject:text];
        NSArray<NSString *> *desktop = NSSearchPathForDirectoriesInDomains(NSDesktopDirectory, NSUserDomainMask, NO);

        if (range.location != 4 || range.length != 5 || NSMaxRange(NSMakeRange(4, 5)) != 9 ||
            items.count != 1 || ![items.firstObject isEqualToString:@"sdk probe"] ||
            ![desktop.firstObject isEqualToString:@"~/Desktop"])
            return 1;

        const unsigned char byte = 42;
        NSData *data = [NSData dataWithBytes:&byte length:1];
        NSError *error = [NSError errorWithDomain:@"sdk.probe" code:7 userInfo:nil];
        NSURL *url = [NSURL URLWithString:@"file:///tmp/sdk-probe"];
        return data.length != 1 || ((const unsigned char *)data.bytes)[0] != byte ||
               error.code != 7 || ![error.domain isEqualToString:@"sdk.probe"] ||
               !url.isFileURL || ![url.path isEqualToString:@"/tmp/sdk-probe"] ||
               [NSNumber numberWithInt:7].integerValue != 7 ||
               [NSDate dateWithTimeIntervalSince1970:42.5].timeIntervalSince1970 != 42.5;
    }
}
