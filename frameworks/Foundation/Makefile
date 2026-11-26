FOUNDATION_TBD_26_5_SHA256 := ec236b8a91637b3d88bff4129ceb2280895e1af55fd3363583433554da445e63
FOUNDATION_TBD_0_0_4_SHA256 := 8d0449b42907aa840dd0f6ac9f2072015ca55e2cc38759f261dde4ee9cc38e9f
FOUNDATION_STAGE = $(STAGE)/Foundation.framework

Foundation: require-stage CoreFoundation-versioned-tbd
	@test -f "$(FOUNDATION_TBD)" || { echo "Set FOUNDATION_TBD to the pinned SDK Gen Foundation stub." >&2; exit 1; }
	$(call stage-framework-headers,Foundation,NSObjCRuntime NSRange NSObject NSString NSPathUtilities NSArray NSDictionary NSEnumerator NSData NSError NSURL NSValue NSNumber NSDate NSRunLoop NSThread NSAutoreleasePool NSLock NSBundle NSUserDefaults NSUserNotification)
	@set -eu; \
		checksum=$$(shasum -a 256 "$(FOUNDATION_TBD)" | cut -d ' ' -f 1); \
		case "$$checksum" in \
			"$(FOUNDATION_TBD_26_5_SHA256)"|"$(FOUNDATION_TBD_0_0_4_SHA256)") ;; \
			*) echo "Unrecognized SDK Gen Foundation stub digest: $$checksum" >&2; exit 1 ;; \
		esac; \
		install -m 644 "$(FOUNDATION_TBD)" "$(FOUNDATION_STAGE)/Foundation.tbd"; \
		patch -s -f -F 0 -V none -p1 -d "$(FOUNDATION_STAGE)" < Foundation/reexport-corefoundation.patch; \
		if test "$$checksum" = "$(FOUNDATION_TBD_0_0_4_SHA256)"; then \
			patch -s -f -F 0 -V none -p1 -d "$(FOUNDATION_STAGE)" < Foundation/versioned-install-name.patch; \
		fi
	mkdir -p "$(FOUNDATION_STAGE)/Versions/C"
	ln -s ../../Foundation.tbd "$(FOUNDATION_STAGE)/Versions/C/Foundation.tbd"

test-Foundation:
	$(call test-sdk-link,Foundation/test.m,-fobjc-arc -framework Foundation -lobjc)

test-Foundation-modules:
	$(call test-objc-modules,Foundation,c++20)
