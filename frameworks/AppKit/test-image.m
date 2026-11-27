#import <AppKit/NSImage.h>

_Static_assert(NSImageCacheDefault == 0 && NSImageCacheNever == 3, "AppKit cache values");
_Static_assert(NSImageResizingModeStretch == 0 && NSImageResizingModeTile == 1, "resizing values");
_Static_assert(NSTIFFCompressionNone == 1 && NSTIFFCompressionLZW == 5, "TIFF values");
_Static_assert(sizeof(NSEdgeInsets) == 4 * sizeof(CGFloat), "edge insets ABI");

int main(void) {
    @autoreleasepool {
        NSImage *image = [NSImage imageWithSystemSymbolName:@"checkmark"
                                    accessibilityDescription:@"Checked"];
        if (!image)
            return 1;
        image.template = YES;
        image.cacheMode = NSImageCacheNever;
        image.capInsets = (NSEdgeInsets){1, 2, 3, 4};
        NSEdgeInsets insets = image.capInsets;
        return !image.isTemplate || image.cacheMode != NSImageCacheNever ||
            insets.top != 1 || insets.left != 2 || insets.bottom != 3 || insets.right != 4;
    }
}
