.DEFAULT_GOAL := test

include ../../frameworks/common.mk

.PHONY: test test-dns-sd test-resolver test-c-libraries test-simd test-framework-free
test: test-dns-sd test-resolver test-c-libraries test-simd test-framework-free

test-dns-sd:
	$(call test-sdk-link,../../components/mDNSResponder/test.c)

test-resolver:
	$(call test-sdk-link,../../components/libresolv/test.c,-lresolv $(application-extension-link))

test-c-libraries:
	$(call test-sdk-link,c-libraries.c,-Xlinker -Z -L"$(SDK)/usr/lib" -liconv -lz -lbsm -lipsec,-Wno-deprecated-declarations)

test-simd:
	$(call test-sdk-link,simd-abi.c)

# Keep host framework search paths out of both links.
framework-free-link = "$(CLANG)" --no-default-config -target arm64-apple-macos11 \
	-isysroot "$(SDK)" -fuse-ld=lld -nostdlib -Wl,-Z -L"$(SDK)/usr/lib" -lSystem libsystem.c

test-framework-free:
	@set -eu; \
		work=$$(mktemp -d "$${TMPDIR:-/tmp}/minimal-sdk.XXXXXX"); \
		trap 'rm -rf -- "$$work"' EXIT; \
		$(framework-free-link) -o "$$work/client"; \
		if test "$(RUN)" = 1; then "$$work/client"; fi; \
		if $(framework-free-link) -framework Foundation -o "$$work/framework-client" 2>"$$work/framework.log"; then \
			echo "Minimal SDK unexpectedly linked Foundation." >&2; exit 1; \
		fi; \
		grep -F 'framework not found for -framework Foundation' "$$work/framework.log"
