FOUNDATION_STAGE = $(STAGE)/Foundation.framework

Foundation: require-stage CoreFoundation-versioned-tbd
	@test -f "$(FOUNDATION_TBD)" || { echo "Set FOUNDATION_TBD to the freshly generated Foundation stub." >&2; exit 1; }
	$(call stage-framework-headers,Foundation,NSObjCRuntime NSRange NSObject NSString NSPathUtilities NSArray NSSet NSDictionary NSEnumerator NSData NSError NSURL NSFileHandle NSJSONSerialization NSValue NSNumber NSDate NSCalendar NSRunLoop NSThread NSAutoreleasePool NSLock NSBundle NSUserDefaults NSUserNotification)
	install -m 644 "$(FOUNDATION_TBD)" "$(FOUNDATION_STAGE)/Foundation.tbd"
	patch -s -f -F 0 -V none -p1 -d "$(FOUNDATION_STAGE)" < Foundation/reexport-corefoundation.patch
	mkdir -p "$(FOUNDATION_STAGE)/Versions/C"
	ln -s ../../Foundation.tbd "$(FOUNDATION_STAGE)/Versions/C/Foundation.tbd"

test-Foundation:
	$(call test-sdk-link,Foundation/test.m,-fobjc-arc -framework Foundation -lobjc)

test-Foundation-modules:
	$(call test-objc-modules,Foundation,c++20)
