.DEFAULT_GOAL := install
PYTHON ?= python3
MIG ?= /usr/bin/mig
sdk-targets := prepare prepare-sources prepare-c-sources prepare-llvm prepare-docc \
	test-llvm-tools generate-sdk compose-sdk test-composed-sdk install install-objc4 test
ifeq ($(strip $(SDK)),)
ifneq ($(filter $(sdk-targets),$(or $(MAKECMDGOALS),$(.DEFAULT_GOAL))),)
$(error Pass an SDK lock name, for example SDK=macosx26.5)
endif
endif

SDK_LOCK := $(CURDIR)/locks/$(SDK).json
INPUTS ?= $(CURDIR)/build/inputs
SOURCE_ROOT ?= $(INPUTS)/sources/$(SDK)$(if $(install-profile),-full)
LLVM_DIR ?= $(INPUTS)/llvm
GENERATED ?= $(CURDIR)/build/generated
SDK_OUTPUT ?= $(CURDIR)/build/sdk
CLANG ?= $(LLVM_DIR)/bin/clang
offline = $(if $(filter 1,$(OFFLINE)),--offline)
export SOURCE_ROOT

.PHONY: prepare prepare-sources prepare-c-sources prepare-llvm prepare-docc prepare-python test-llvm-tools
prepare: prepare-sources prepare-llvm prepare-docc prepare-python

prepare-c-sources:
	"$(PYTHON)" -m tools.fetch_sources --lock "$(SDK_LOCK)" --dest "$(INPUTS)/sources/$(SDK)" --cache "$(INPUTS)/git" $(offline)

prepare-sources: prepare-c-sources
	"$(PYTHON)" -m tools.fetch_sources --lock "$(SDK_LOCK)" --full --dest "$(INPUTS)/sources/$(SDK)-full" --cache "$(INPUTS)/git" $(offline)

prepare-llvm:
	"$(PYTHON)" -m tools.fetch_llvm_tools --lock "$(SDK_LOCK)" --dest "$(LLVM_DIR)" --cache "$(INPUTS)/downloads" $(offline)

prepare-docc:
	PYTHON="$(PYTHON)" bash tools/fetch_docc_snapshot.sh "$(SDK_LOCK)" "$(INPUTS)/docc" "$(INPUTS)/downloads" $(offline)

prepare-python:
	@set -eu; \
		venv="$(INPUTS)/python"; \
		digest=$$(shasum -a 256 release/requirements.txt | cut -d ' ' -f 1); \
		if test -x "$$venv/bin/python" && test -f "$$venv/.requirements-sha256" && \
			test "$$(cat "$$venv/.requirements-sha256")" = "$$digest"; then exit 0; fi; \
		test "$(OFFLINE)" != 1 || { echo "Offline mode requires the prepared Python environment: $$venv" >&2; exit 1; }; \
		"$(PYTHON)" -m venv "$$venv"; \
		"$$venv/bin/python" -m pip install --require-hashes --only-binary=:all: -r release/requirements.txt; \
		printf '%s\n' "$$digest" > "$$venv/.requirements-sha256"

test-llvm-tools:
	PYTHONPATH="$(CURDIR)" "$(PYTHON)" tests/check_llvm_tools.py --lock "$(SDK_LOCK)" --llvm-dir "$(LLVM_DIR)"

.PHONY: generate-sdk compose-sdk test-composed-sdk
generate-sdk:
	PYTHON="$(PYTHON)" bash tools/fetch_docc_snapshot.sh "$(SDK_LOCK)" "$(INPUTS)/docc" "$(INPUTS)/downloads" --verify
	@set -eu; \
		version=$$("$(PYTHON)" -c 'import json,sys; print(json.load(open(sys.argv[1]))["sdk"]["version"])' "$(SDK_LOCK)"); \
		"$(INPUTS)/python/bin/python" -m tools.apple_sdk_gen --sdk-version "$$version" \
			--llvm-dir "$(LLVM_DIR)" --docc-cache-only --cache-dir "$(INPUTS)/docc" \
			--output "$(GENERATED)" $(if $(filter undefined,$(origin FRAMEWORKS)),,--frameworks "$(FRAMEWORKS)") -v

compose-sdk:
	INPUTS="$(INPUTS)" LLVM_DIR="$(LLVM_DIR)" FRAMEWORKS="$(FRAMEWORKS)" PATH="$(INPUTS)/python/bin:$$PATH" \
		bash release/build-composed-sdk.sh "$(SDK_LOCK)" \
		"$(GENERATED)/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk" "$(SDK_OUTPUT)"

test-composed-sdk:
	INPUTS="$(INPUTS)" LLVM_DIR="$(LLVM_DIR)" PATH="$(INPUTS)/python/bin:$$PATH" \
		bash release/test-composed-sdk.sh "$(SDK_LOCK)" "$(SDK_OUTPUT)"

.PHONY: install install-objc4 check-c-install-tools test
install: check-c-install-tools
install-objc4: install-profile := objc4

install install-objc4:
	@set -eu; \
		test -n "$(OUT)" && test ! -e "$(OUT)" || { echo "Set OUT to a new directory." >&2; exit 1; }; \
		stage=$$(mktemp -d "$${TMPDIR:-/tmp}/apple-oss-c-recipes.XXXXXX"); \
		trap 'rm -rf -- "$$stage"' EXIT; \
		"$(PYTHON)" -m tools.fetch_sources --verify --lock "$(SDK_LOCK)" $(if $(install-profile),--full) \
			--dest "$(SOURCE_ROOT)" --record "$$stage/source-lock.json"; \
		$(MAKE) $(if $(install-profile),build-$(install-profile),build-install) \
			STAGE="$$stage" SOURCE_ROOT="$(SOURCE_ROOT)" CLANG="$(CLANG)" MIG="$(MIG)" OUT="$(OUT)"

check-c-install-tools:
	@test -x "$(CLANG)" || { echo "Set CLANG to the pinned LLVM Clang executable." >&2; exit 1; }
	@test -x "$(MIG)" || { echo "Set MIG to the system MIG executable." >&2; exit 1; }

test:
	@test -x "$(CLANG)" || { echo "Set CLANG to the pinned LLVM Clang executable." >&2; exit 1; }
	@test -n "$(OUT)" && test -f "$(OUT)/header-manifest.tsv" || { echo "Set OUT to the tree produced by make install." >&2; exit 1; }
	@cmp -s "locks/$(SDK).json" "$(OUT)/source-lock.json" || { echo "OUT was not built with the $(SDK) source lock." >&2; exit 1; }
	C_INSTALL="$(abspath $(OUT))" $(PYTHON) -m unittest discover -s tests/header_install
	$(PYTHON) tests/installed_headers/compile_probes.py --clang "$(CLANG)" --sysroot "$(OUT)" \
		--fixture tests/installed_headers/fenv_abi.c \
		--fixture tests/installed_headers/libm_scalar_pi.c \
		--fixture tests/installed_headers/libm_paired_trig.c \
		--fixture tests/installed_headers/darwin_consumer_headers.c \
		--fixture components/mDNSResponder/test.c \
		--fixture components/libresolv/test.c \
		--fixture tests/installed_headers/stdatomic_init.c \
		$(if $(filter-out macosx26.5,$(SDK)),,--fixture tests/installed_headers/macos_26_5_availability.c) \
		$(if $(filter-out macosx26.5,$(SDK)),,--fixture tests/installed_headers/libm_half.c) \
		$(if $(filter-out macosx26.5,$(SDK)),,--fixture tests/installed_headers/security_dependencies.c) \
		--fixture tests/installed_headers/complex_abi.c \
		--fixture tests/installed_headers/target_conditionals.c
	$(PYTHON) tests/installed_headers/check_fenv_runtime.py

ifneq ($(strip $(STAGE)),)
# Each copy writes its full receipt as it stages the file.
recipe-path = $(or $(2),components/$(1)/Makefile)
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
/bin/sh components/record-installed.sh "$(STAGE)/$(1)" "$(1)" "$(2)" "$(3)" "$(4)" $(5) >> "$(STAGE)/$(1)/records"
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

include $(wildcard components/*/Makefile)

pre-mig: stage
	/bin/sh components/merge.sh --bootstrap "$(STAGE)/pre-mig" "$(STAGE)"/*/records

build-install: mig-arm64
	SOURCE_LOCK="$(STAGE)/source-lock.json" /bin/sh components/merge.sh "$(OUT)" "$(STAGE)"/*/records

build-objc4: stage-objc4
	SOURCE_LOCK="$(STAGE)/source-lock.json" /bin/sh components/merge.sh "$(OUT)" "$(STAGE)/objc4/records"
endif
