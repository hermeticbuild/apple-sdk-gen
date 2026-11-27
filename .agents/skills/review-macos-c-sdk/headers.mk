# Run from the repository root after make install and make test.
PYTHON ?= python3
MINIMUM ?= 11.0
SDK ?= macosx26.5
CLANG = $(LLVM)/bin/clang
SKILL := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
HEADERS = $(SKILL)scripts/sdk_review/headers
BASELINE = $(wildcard $(HEADERS)/data/$(SDK)/inventory.json)
ROOTS = tests/installed_headers/default_profile.c
DISCOVERY = $(HEADERS)/fixtures/sdk_discovery.c
export PYTHONPATH := $(SKILL)scripts$(if $(PYTHONPATH),:$(PYTHONPATH))

.PHONY: header-backlog census paths discovery semantics inputs test
inputs:
	@test -x "$(CLANG)" && test -f "$(C_INSTALL)/header-manifest.tsv" && test -f "$(APPLE_SDK)/SDKSettings.json" || { echo "Set LLVM, C_INSTALL and APPLE_SDK" >&2; exit 2; }
	@test -n "$(WORK)" || { echo "Set WORK to a local report directory" >&2; exit 2; }
	@test "$$("/usr/bin/plutil" -extract CanonicalName raw -o - "$(APPLE_SDK)/SDKSettings.json")" = "$(SDK)" || { echo "SDK must match the reference SDK's CanonicalName" >&2; exit 2; }
	@mkdir -p "$(WORK)"

census: inputs
	$(PYTHON) -m sdk_review.headers.census --clang "$(CLANG)" --c-install "$(C_INSTALL)" --minimum "$(MINIMUM)" --out "$(WORK)/census.json" --report-only

paths: inputs
	$(PYTHON) -m sdk_review.headers.trace_includes --probe "$(ROOTS)" --clang "$(CLANG)" --sysroot "$(C_INSTALL)" --out "$(WORK)/generated.json"
	$(PYTHON) -m sdk_review.headers.trace_includes --probe "$(ROOTS)" --clang "$(CLANG)" --sysroot "$(APPLE_SDK)" --out "$(WORK)/reference.json"
	$(PYTHON) -m sdk_review.headers.audit_sdk_headers --sdk "$(APPLE_SDK)" --installation "$(C_INSTALL)" --clang "$(CLANG)" --reference "$(WORK)/reference.json" --generated-probe "$(WORK)/generated.json" $(if $(BASELINE),--baseline "$(BASELINE)") --out "$(WORK)/header-audit.json" --review-out "$(WORK)/header-review.md"

semantics: inputs
	$(PYTHON) -m sdk_review.headers.compare_c_interfaces --clang "$(CLANG)" --installation "$(C_INSTALL)" --sdk "$(APPLE_SDK)" --out "$(WORK)/semantics.json"

.PHONY: malloc-backdeploy
malloc-backdeploy: inputs
	@test -x "$(APPLE_CLANG)" || { echo "Set APPLE_CLANG to Xcode's Apple Clang executable" >&2; exit 2; }
	$(PYTHON) -m sdk_review.headers.verify_malloc_backdeploy --apple-clang "$(APPLE_CLANG)" \
		--llvm-nm "$(LLVM)/bin/llvm-nm" --installation "$(C_INSTALL)" --sdk "$(APPLE_SDK)" --work "$(WORK)"

discovery: inputs
	$(PYTHON) -m sdk_review.headers.trace_includes --report-only --probe "$(DISCOVERY)" --clang "$(CLANG)" --sysroot "$(C_INSTALL)" --out "$(WORK)/discovery-generated.json"
	$(PYTHON) -m sdk_review.headers.trace_includes --report-only --probe "$(DISCOVERY)" --clang "$(CLANG)" --sysroot "$(APPLE_SDK)" --out "$(WORK)/discovery-reference.json"

header-backlog: census paths semantics discovery
	$(PYTHON) -m sdk_review.headers.header_backlog --c-install "$(C_INSTALL)" --census "$(WORK)/census.json" --sdk-audit "$(WORK)/header-audit.json" --semantic "$(WORK)/semantics.json" --reference-sdk "$(APPLE_SDK)" --clang "$(CLANG)" --out "$(WORK)/header-backlog.json"

test:
	LLVM="$(LLVM)" LIBSYSTEM_TEST_LLVM="$(LLVM)" $(PYTHON) -m unittest discover -s "$(SKILL)scripts/sdk_review" -t "$(SKILL)scripts"

.PHONY: complex-runtime complex-arm64
complex-runtime: complex-arm64

# Compile against the generated headers. Only the link step reads reference stubs.
complex-arm64: complex-%: inputs
	env -i PATH=/usr/bin:/bin LC_ALL=C "$(CLANG)" --no-default-config -target "$*-apple-macos$(MINIMUM)" \
		-isysroot "$(C_INSTALL)" -nostdinc -isystem "$$("$(CLANG)" --no-default-config -print-resource-dir)/include" \
		-isystem "$(C_INSTALL)/usr/include" -std=c11 -c tests/installed_headers/complex_abi.c -o "$(WORK)/complex-$*.o"
	"$(LLVM)/bin/ld64.lld" -arch "$*" -platform_version macos "$(MINIMUM)" "$(patsubst macosx%,%,$(SDK))" \
		-syslibroot "$(APPLE_SDK)" "$(WORK)/complex-$*.o" -lSystem -o "$(WORK)/complex-$*"
	"$(WORK)/complex-$*"
