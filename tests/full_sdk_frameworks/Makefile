.DEFAULT_GOAL := test

include ../../frameworks/common.mk

FRAMEWORK_TESTS := test-foundation-macros test-coregraphics test-security test-network \
	test-modelio test-modelio-modules test-objc-property test-autosync-reminder test-charconv
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

test-autosync-reminder:
	$(call test-sdk-link,autosync-reminder.m,-framework UserNotifications -framework AppKit -framework Foundation -lobjc,-fobjc-arc)

test-charconv:
	@set -eu; \
	work=$$(mktemp -d "$${TMPDIR:-/tmp}/charconv-test.XXXXXX"); \
	trap 'rm -rf -- "$$work"' EXIT; \
	set -- "$(CLANG)" --driver-mode=g++ --no-default-config -isysroot "$(SDK)" \
		-nostdinc++ -isystem "$(SDK)/usr/include/c++/v1" -std=c++17 charconv.cpp; \
	"$$@" -target arm64-apple-macos26.0 -fuse-ld=lld -o "$$work/charconv"; \
	if test "$(RUN)" = 1; then "$$work/charconv"; fi; \
	if "$$@" -target arm64-apple-macos15.0 -fsyntax-only > "$$work/mac15.log" 2>&1; then \
		echo "Floating-point from_chars unexpectedly accepted a macOS 15 target." >&2; exit 1; \
	fi; \
	grep -F 'introduced in macOS 26.0' "$$work/mac15.log" >/dev/null || { cat "$$work/mac15.log" >&2; exit 1; }

# Run these separately to reproduce known gaps.
test-avrouting:
	$(call test-sdk-link,avrouting.m,-framework AVRouting -lobjc,-fobjc-arc)

test-metalkit:
	$(call test-sdk-link,metalkit.m,-framework MetalKit -lobjc,-fobjc-arc)
