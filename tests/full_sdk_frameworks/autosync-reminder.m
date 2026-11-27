#import <UserNotifications/UserNotifications.h>
#import <AppKit/NSAlert.h>
#import <Foundation/NSCalendar.h>
#import <Foundation/NSFileHandle.h>
#import <Foundation/NSJSONSerialization.h>
#import <Foundation/NSSet.h>

int main(void) {
    @autoreleasepool {
        NSDateComponents *date = [NSDateComponents new];
        date.hour = 8;
        date.minute = 15;
        UNCalendarNotificationTrigger *trigger =
            [UNCalendarNotificationTrigger triggerWithDateMatchingComponents:date repeats:YES];
        NSSet<UNCalendarNotificationTrigger *> *triggers = [NSSet setWithObject:trigger];
        NSData *data = [NSJSONSerialization dataWithJSONObject:@[@"reminder"] options:0 error:NULL];
        NSArray *value = [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL];
        return ![triggers containsObject:trigger] || date.hour != 8 || value.count != 1 ||
            ![NSFileHandle fileHandleWithStandardError] || ![NSAlert class];
    }
}
