#import <Cocoa/Cocoa.h>
#import <AppKit/NSColor.h>
#import <CoreData/NSEntityDescription.h>

int main(void) {
    @autoreleasepool {
        NSColor *color = [NSColor colorWithSRGBRed:0.25 green:0.5 blue:0.75 alpha:1];
        NSString *description = color.description;
        NSManagedObjectModel *model = [[NSManagedObjectModel alloc] init];
        NSEntityDescription *entity = [NSEntityDescription new];
        entity.name = @"TrialEntity";
        model.entities = [NSArray arrayWithObject:entity];
        NSMutableDictionary<NSString *, NSNumber *> *counts = [NSMutableDictionary dictionaryWithCapacity:1];
        counts[@"images"] = [NSNumber numberWithInt:1];
        NSImage *image = [[NSImage alloc] initWithSize:NSMakeRect(0, 0, 80, 40).size];
        NSEvent *event = [NSEvent otherEventWithType:NSEventTypeApplicationDefined
                                           location:NSZeroPoint modifierFlags:0 timestamp:0
                                       windowNumber:0 context:nil
                                            subtype:NSEventSubtypeApplicationActivated data1:0 data2:0];

        return !NSPasteboardTypeHTML.length || !NSPasteboardTypeString.length ||
               !NSPasteboardTypeTIFF.length || !NSPasteboardURLReadingFileURLsOnlyKey.length ||
               color.redComponent != 0.25 || color.greenComponent != 0.5 ||
               color.blueComponent != 0.75 || color.alphaComponent != 1 ||
               description.length == 0 || model.entities.count != 1 ||
               ![model.entities.firstObject.name isEqualToString:@"TrialEntity"] ||
               counts[@"images"].integerValue != 1 || image.size.width != 80 || image.size.height != 40 ||
               event.type != NSEventTypeApplicationDefined || event.subtype != NSEventSubtypeApplicationActivated ||
               ![NSSlider isSubclassOfClass:[NSControl class]] ||
               ![NSWindow isSubclassOfClass:[NSResponder class]] ||
               ![NSView isSubclassOfClass:[NSResponder class]] ||
               ![NSApplication isSubclassOfClass:[NSResponder class]];
    }
}
