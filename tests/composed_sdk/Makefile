.DEFAULT_GOAL := test

include ../../frameworks/common.mk

.PHONY: test test-dns-sd test-resolver test-frameworks test-foundation-macros \
	test-coregraphics test-security test-network test-avrouting test-simd test-modelio test-modelio-modules test-metalkit test-objc-property
test: test-dns-sd test-resolver

test-frameworks: test-foundation-macros test-coregraphics test-security test-network \
	test-avrouting test-simd test-modelio test-modelio-modules test-metalkit test-objc-property

test-dns-sd:
	$(call test-sdk-link,../../components/mDNSResponder/test.c)

test-resolver:
	$(call test-sdk-link,../../components/libresolv/test.c,-lresolv $(application-extension-link))

test-foundation-macros:
	$(call test-sdk-link,foundation-macros.m,-framework Foundation -lobjc,-fobjc-arc)

test-coregraphics:
	$(call test-sdk-link,coregraphics.m,-framework CoreGraphics -framework CoreFoundation,-fobjc-arc)

test-security:
	$(call test-sdk-link,security.m,-framework Security -framework CoreFoundation,-fobjc-arc)

test-network:
	$(call test-sdk-link,network.m,-framework Network -lobjc,-fobjc-arc)

test-avrouting:
	$(call test-sdk-link,avrouting.m,-framework AVRouting -lobjc,-fobjc-arc)

test-simd:
	$(call test-sdk-link,simd-abi.c)

test-modelio:
	$(call test-sdk-link,modelio.m,-framework ModelIO -lobjc,-fobjc-arc)

test-modelio-modules:
	$(call test-sdk-link,modelio.m,-framework ModelIO -lobjc -lc++ -lc++abi,\
	    -x objective-c++ -std=c++20 -fobjc-arc -fmodules -fcxx-modules -fmodules-cache-path="$$work/modules")

test-objc-property:
	$(call test-sdk-link,objc-property.m,-framework Foundation -lobjc,-fno-objc-arc)

test-metalkit:
	$(call test-sdk-link,metalkit.m,-framework MetalKit -lobjc,-fobjc-arc)
