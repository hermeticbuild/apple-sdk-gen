Cocoa: require-stage Foundation AppKit CoreData
	@test -f "$(COCOA_FRAMEWORK)/Headers/Cocoa.h" || { echo "Set COCOA_FRAMEWORK to the freshly generated Cocoa bundle." >&2; exit 1; }
	cp -RP "$(COCOA_FRAMEWORK)" "$(STAGE)/Cocoa.framework"

test-Cocoa:
	$(call test-sdk-link,Cocoa/test.m,-fobjc-arc -framework Cocoa -lobjc)

test-Cocoa-modules:
	$(call test-objc-modules,Cocoa)
