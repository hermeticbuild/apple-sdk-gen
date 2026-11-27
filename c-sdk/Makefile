.DEFAULT_GOAL := install
PYTHON ?= python3
MIG ?= /usr/bin/mig
SDK ?= macosx26.5
SOURCE_ROOT ?= $(CURDIR)/build/sources/$(SDK)$(if $(install-profile),-$(install-profile))
export SOURCE_ROOT

.PHONY: install install-objc4 check-c-install-tools test
install: check-c-install-tools
install-objc4: install-profile := objc4

install install-objc4:
	@set -eu; \
		test -n "$(OUT)" && test ! -e "$(OUT)" || { echo "Set OUT to a new directory." >&2; exit 1; }; \
		stage=$$(mktemp -d "$${TMPDIR:-/tmp}/apple-oss-c-recipes.XXXXXX"); \
		trap 'rm -rf -- "$$stage"' EXIT; \
		"$(PYTHON)" -m tools.sources.locked_sources verify --sdk "$(SDK)" \
			$(if $(install-profile),--profile "$(install-profile)") \
			--source-root "$(SOURCE_ROOT)" --record "$$stage/source-lock.json"; \
		$(MAKE) $(if $(install-profile),build-$(install-profile),build-install) \
			STAGE="$$stage" SOURCE_ROOT="$(SOURCE_ROOT)" CLANG="$(CLANG)" MIG="$(MIG)" OUT="$(OUT)"

check-c-install-tools:
	@test -x "$(CLANG)" || { echo "Set CLANG to the pinned LLVM Clang executable." >&2; exit 1; }
	@test -x "$(MIG)" || { echo "Set MIG to the system MIG executable." >&2; exit 1; }

test:
	@test -x "$(CLANG)" || { echo "Set CLANG to the pinned LLVM Clang executable." >&2; exit 1; }
	@test -n "$(OUT)" && test -f "$(OUT)/header-manifest.tsv" || { echo "Set OUT to the tree produced by make install." >&2; exit 1; }
	@cmp -s "locks/$(SDK).json" "$(OUT)/source-lock.json" || { echo "OUT was not built with the $(SDK) source lock." >&2; exit 1; }
	C_INSTALL="$(abspath $(OUT))" $(PYTHON) -m unittest discover -s tests/recipes
	$(PYTHON) tests/installed_headers/compile_probes.py --clang "$(CLANG)" --sysroot "$(OUT)" \
		--fixture tests/installed_headers/fenv_abi.c \
		--fixture tests/installed_headers/libm_scalar_pi.c \
		--fixture tests/installed_headers/libm_paired_trig.c \
		--fixture tests/installed_headers/darwin_consumer_headers.c \
		--fixture recipes/mDNSResponder/test.c \
		--fixture recipes/libresolv/test.c \
		--fixture tests/installed_headers/stdatomic_init.c \
		$(if $(filter-out macosx26.5,$(SDK)),,--fixture tests/installed_headers/macos_26_5_availability.c) \
		$(if $(filter-out macosx26.5,$(SDK)),,--fixture tests/installed_headers/libm_half.c) \
		$(if $(filter-out macosx26.5,$(SDK)),,--fixture tests/installed_headers/security_dependencies.c) \
		--fixture tests/installed_headers/complex_abi.c \
		--fixture tests/installed_headers/target_conditionals.c
	$(PYTHON) tests/installed_headers/check_fenv_runtime.py

C_ARCHIVE ?= $(CURDIR)/build/apple-oss-c-headers-$(SDK).tar.zst

.PHONY: c-archive
c-archive: install test
	mkdir -p "$(dir $(C_ARCHIVE))"
	"$(PYTHON)" -m tools.pack_archive --source "$(OUT)" \
		--root-name "apple-oss-c-headers-$(SDK)" --output "$(C_ARCHIVE)"

# The tests must see the tree produced by install even with parallel Make.
ifneq ($(filter c-archive,$(MAKECMDGOALS)),)
test: install
endif

ifneq ($(strip $(STAGE)),)
# Each copy writes its full receipt as it stages the file.
recipe-path = $(or $(2),recipes/$(1)/Makefile)
define copy-headers
mkdir -p "$(STAGE)/$(1)/dst/usr/include/$(2)"
@set -e; for source in $(3); do \
	install -m 644 "$$SOURCE_ROOT/$${source#sources/}" "$(STAGE)/$(1)/dst/usr/include/$(2)/"; \
	path="$(if $(filter .,$(2)),usr/include,usr/include/$(2))/$${source##*/}"; \
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$$path" "$(1)" "$$source" \
		"$(call recipe-path,$(1),$(4))" copy "$(call recipe-path,$(1),$(4))" "$$source"; \
	done >> "$(STAGE)/$(1)/records"
endef

define record-installed
/bin/sh recipes/record-installed.sh "$(STAGE)/$(1)" "$(1)" "$(2)" "$(3)" "$(4)" $(5) >> "$(STAGE)/$(1)/records"
endef

# Apply package patches only to staged files, with exact hunk context.
define apply-recipe-patch
patch -s -f -F 0 -V none -p1 -d "$(1)" < "$(2)"
endef

define header-record
@{ printf '%s\t%s\t%s\t%s\t%s' "$(2)" "$(1)" "$(3)" "$(4)" "$(5)"; \
	for input in $(6); do printf '\t%s' "$$input"; done; printf '\n'; } \
	>> "$(STAGE)/$(1)/records"
endef

.PHONY: stage build-install build-objc4 pre-mig
stage:

include $(wildcard recipes/*/Makefile)

pre-mig: stage
	/bin/sh recipes/merge.sh --bootstrap "$(STAGE)/pre-mig" "$(STAGE)"/*/records

build-install: mig-arm64
	SOURCE_LOCK="$(STAGE)/source-lock.json" /bin/sh recipes/merge.sh "$(OUT)" "$(STAGE)"/*/records

build-objc4: stage-objc4
	SOURCE_LOCK="$(STAGE)/source-lock.json" /bin/sh recipes/merge.sh "$(OUT)" "$(STAGE)/objc4/records"
endif
