# Read pinned Git objects directly. A working checkout or a bare repo works.
define prepare-source
@set -eu; \
	repo="$(SOURCE_ROOT)/$(1)"; \
	if test ! -e "$$repo"; then \
		mkdir -p "$(SOURCE_ROOT)"; \
		temp=$$(mktemp -d "$(SOURCE_ROOT)/.fetch-$(1).XXXXXX"); \
		trap 'rm -rf -- "$$temp"' EXIT; \
		git init --quiet --bare "$$temp"; \
		git -C "$$temp" fetch --quiet --depth=1 --no-tags \
			"https://github.com/apple-oss-distributions/$(1).git" "$(2)"; \
		git -C "$$temp" cat-file -e "$(2)^{commit}"; \
		mv "$$temp" "$$repo"; \
	else \
		git -C "$$repo" cat-file -e "$(2)^{commit}"; \
	fi
endef

# Emit only the format shared by the small C framework stubs.
define write-tbd
@set -eu; \
	targets='[ arm64-macos ]'; \
	{ \
		printf '%s\n' '--- !tapi-tbd' 'tbd-version: 4' "targets: $$targets" \
			"install-name: '/System/Library/Frameworks/$(1).framework/$(1)'"; \
		if test -n "$(2)"; then \
			symbols=$$(LC_ALL=C sort -u "$(2)"); \
			test -n "$$symbols"; \
			printf 'exports:\n  - targets: %s\n    symbols: [' "$$targets"; \
			separator=' '; \
			for symbol in $$symbols; do \
				printf "%s'_%s'" "$$separator" "$$symbol"; \
				separator=', '; \
			done; \
			printf ' ]\n'; \
		fi; \
		printf '%s\n' '...'; \
	} > "$(STAGE)/$(1).framework/$(1).tbd"
endef

define stage-framework-headers
	mkdir -p "$(STAGE)/$(1).framework/Headers" "$(STAGE)/$(1).framework/Modules"
	install -m 644 $(1)/Headers/*.h "$(STAGE)/$(1).framework/Headers/"
	@set -eu; { \
		printf 'framework module %s [system] {\n  umbrella header "%s.h"\n' '$(1)' '$(1)'; \
		for name in $(2); do \
			header="$(STAGE)/$(1).framework/Headers/$$name.h"; \
			if test ! -f "$$header"; then printf '#import <%s/%s.h>\n' '$(1)' '$(1)' > "$$header"; fi; \
			printf '  textual header "%s.h"\n' "$$name"; \
		done; \
		printf '  export *\n  module * { export * }\n}\n'; \
	} > "$(STAGE)/$(1).framework/Modules/module.modulemap"
endef

define stage-local-framework
	$(call stage-framework-headers,$(1))
	$(call write-tbd,$(1),$(2))
endef

# Protect the source and the final output from direct staging invocations.
.PHONY: require-stage
require-stage:
	@test -n "$(STAGE)" && test -d "$(STAGE)" || { echo "Run make install to stage frameworks." >&2; exit 1; }

CLANG_INSTALLAPI ?= $(dir $(CLANG))clang-installapi
INSTALLAPI_MIN ?= 11.0
objc-installapi = -iframework"$(STAGE)" -isystem "$(OBJC4_INSTALL)/usr/include" --filetype=tbd-v4 -fobjc-arc

# InstallAPI can report a header error even when it returns success.
define installapi
@set -eu; \
	test -x "$(CLANG)" && test -x "$(CLANG_INSTALLAPI)" && test -n "$(C_INSTALL)" && test -d "$(C_INSTALL)/usr/include" \
		|| { echo "Set CLANG to the pinned LLVM projection and C_INSTALL to the generated C tree." >&2; exit 1; }; \
	resource=$$("$(CLANG)" --no-default-config -print-resource-dir); \
	diagnostics=$$(mktemp "$${TMPDIR:-/tmp}/installapi.XXXXXX"); \
	trap 'rm -f -- "$$diagnostics"' EXIT; \
	if ! "$(CLANG_INSTALLAPI)" -x "$(or $(3),c)" -nostdinc -isysroot "$(C_INSTALL)" \
		-isystem "$$resource/include" -isystem "$(C_INSTALL)/usr/include" \
		-dynamiclib -target "arm64-apple-macos$(INSTALLAPI_MIN)" \
		$(1) -o "$(2)" 2>"$$diagnostics" || test -s "$$diagnostics"; then \
		cat "$$diagnostics" >&2; exit 1; \
	fi
endef

test-clang = "$(CLANG)" --no-default-config -target "$$cpu-apple-macos14.0" -isysroot "$(SDK)" \
	-nostdinc -isystem "$$resource/include" -isystem "$(SDK)/usr/include" \
	-iframework "$(SDK)/System/Library/Frameworks" -std=c11 -Werror

SDK_TEST_ARCHS := arm64

define test-sdk-link
@set -eu; \
	work=$$(mktemp -d "$${TMPDIR:-/tmp}/framework-tests.XXXXXX"); \
	trap 'rm -rf -- "$$work"' EXIT; \
	resource=$$("$(CLANG)" --no-default-config -print-resource-dir); \
	for cpu in $(SDK_TEST_ARCHS); do \
		$(test-clang) $(3) -fuse-ld=lld -nostdlib "$(1)" $(2) -lSystem -o "$$work/test-$$cpu"; \
		if test "$(RUN)" = 1; then "$$work/test-$$cpu"; fi; \
		echo "$$cpu $(@:test-%=%) link probe passed"; \
	done
endef

test-framework-link = $(call test-sdk-link,$(1)/test.c,-framework "$(1)" $(2))
test-objc-modules = $(call test-sdk-link,$(1)/test.m,-fobjc-arc -framework "$(1)" -lobjc -lc++ -lc++abi,\
	-x objective-c++ -std=$(or $(2),c++17) -fmodules -fcxx-modules -fmodules-cache-path="$$work/modules")

# Treat an unsafe-dylib diagnostic as a failed link probe.
application-extension-link = -fapplication-extension -Wl,-fatal_warnings

define test-framework-headers
@set -eu; \
	resource=$$("$(CLANG)" --no-default-config -print-resource-dir); \
	for cpu in $(SDK_TEST_ARCHS); do \
		$(test-clang) -fsyntax-only "$(1)/$(or $(2),test.c)"; \
		echo "$$cpu $(1) header probe passed"; \
	done
endef
