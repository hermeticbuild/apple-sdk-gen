APPKIT_STAGE = $(STAGE)/AppKit.framework

AppKit: require-stage Foundation QuartzCore
AppKit: $(filter ApplicationServices CoreGraphics,$(FRAMEWORKS))
	@test -f "$(OBJC4_INSTALL)/usr/include/objc/NSObject.h" || { echo "Set OBJC4_INSTALL to the pinned objc4 installation." >&2; exit 1; }
	$(call stage-framework-headers,AppKit,NSColor NSResponder NSApplication NSEvent NSGraphicsContext NSScreen NSView NSCell NSControl NSSlider NSTextField NSImage NSImageRep NSBitmapImageRep NSWindow)
	$(call installapi,$(objc-installapi) \
		-install_name /System/Library/Frameworks/AppKit.framework/Versions/C/AppKit \
		-reexport_library "$(FOUNDATION_STAGE)/Foundation.tbd" \
		$(if $(filter ApplicationServices,$(FRAMEWORKS)),-reexport_library "$(APPLICATION_SERVICES_STAGE)/ApplicationServices.tbd") \
		-extra-public-header "$(APPKIT_STAGE)/Headers/AppKit.h",$(APPKIT_STAGE)/AppKit.tbd,objective-c)
	mkdir -p "$(APPKIT_STAGE)/Versions/C"
	ln -s ../../AppKit.tbd "$(APPKIT_STAGE)/Versions/C/AppKit.tbd"
