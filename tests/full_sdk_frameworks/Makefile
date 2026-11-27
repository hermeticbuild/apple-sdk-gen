.DEFAULT_GOAL := test

include ../../frameworks/common.mk

FRAMEWORK_TESTS := test-foundation-macros test-coregraphics test-security test-network \
	test-modelio test-modelio-modules test-objc-property
.PHONY: test $(FRAMEWORK_TESTS) test-avrouting test-metalkit
test: $(FRAMEWORK_TESTS)

test-foundation-macros:
	$(call test-sdk-link,foundation-macros.m,-framework Foundation -lobjc,-fobjc-arc)

test-coregraphics:
	$(call test-sdk-link,coregraphics.m,-framework CoreGraphics -framework CoreFoundation,-fobjc-arc)

test-security:
	$(call test-sdk-link,security.m,-framework Security -framework CoreFoundation,-fobjc-arc)

test-network:
	$(call test-sdk-link,network.m,-framework Network -lobjc,-fobjc-arc)

test-modelio:
	$(call test-sdk-link,modelio.m,-framework ModelIO -lobjc,-fobjc-arc)

test-modelio-modules:
	$(call test-sdk-link,modelio.m,-framework ModelIO -lobjc -lc++ -lc++abi,\
	    -x objective-c++ -std=c++20 -fobjc-arc -fmodules -fcxx-modules -fmodules-cache-path="$$work/modules")

test-objc-property:
	$(call test-sdk-link,objc-property.m,-framework Foundation -lobjc,-fno-objc-arc)

# Run these separately to reproduce known gaps.
test-avrouting:
	$(call test-sdk-link,avrouting.m,-framework AVRouting -lobjc,-fobjc-arc)

test-metalkit:
	$(call test-sdk-link,metalkit.m,-framework MetalKit -lobjc,-fobjc-arc)
