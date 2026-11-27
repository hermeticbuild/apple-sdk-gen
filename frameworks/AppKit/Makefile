APPKIT_STAGE = $(STAGE)/AppKit.framework
APPKIT_DOCC_HEADER = $(GENERATED_FRAMEWORKS)/AppKit.framework/Headers/AppKit.h

AppKit: require-stage Foundation QuartzCore
AppKit: $(filter ApplicationServices CoreGraphics,$(FRAMEWORKS))
	@test -f "$(OBJC4_INSTALL)/usr/include/objc/NSObject.h" || { echo "Set OBJC4_INSTALL to the pinned objc4 installation." >&2; exit 1; }
	$(call stage-framework-headers,AppKit,NSColor NSResponder NSApplication NSEvent NSGraphicsContext NSScreen NSView NSCell NSControl NSSlider NSTextField NSAlert NSImage NSImageRep NSBitmapImageRep NSWindow)
	@set -eu; \
		declarations=$$(sed -n '/^@interface NSImage[[:space:]]*:/,/^@end$$/p' "$(APPKIT_DOCC_HEADER)"); \
		test -n "$$declarations" || { echo "Missing NSImage declaration in $(APPKIT_DOCC_HEADER)." >&2; exit 1; }; \
		{ cat AppKit/NSImage-preamble.h; printf '\n%s\n\n#endif\n' "$$declarations"; } \
			> "$(APPKIT_STAGE)/Headers/NSImage.h"
	$(call installapi,$(objc-installapi) \
		-install_name /System/Library/Frameworks/AppKit.framework/Versions/C/AppKit \
		-reexport_library "$(FOUNDATION_STAGE)/Foundation.tbd" \
		$(if $(filter ApplicationServices,$(FRAMEWORKS)),-reexport_library "$(APPLICATION_SERVICES_STAGE)/ApplicationServices.tbd") \
		-extra-public-header "$(APPKIT_STAGE)/Headers/AppKit.h" \
		-extra-public-header "$(APPKIT_STAGE)/Headers/NSImage.h",$(APPKIT_STAGE)/AppKit.tbd,objective-c)
	mkdir -p "$(APPKIT_STAGE)/Versions/C"
	ln -s ../../AppKit.tbd "$(APPKIT_STAGE)/Versions/C/AppKit.tbd"

.PHONY: test-AppKit-exports test-AppKit-image
test-AppKit-exports:
	$(call test-sdk-link,AppKit/test-exports.c,-framework AppKit)

test-AppKit-image:
	$(call test-sdk-link,AppKit/test-image.m,-framework AppKit -framework Foundation -lobjc,-fobjc-arc)
