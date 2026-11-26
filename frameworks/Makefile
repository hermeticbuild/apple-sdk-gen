.DEFAULT_GOAL := install

SOURCE_ROOT ?= $(abspath ../build/framework-sources)
OUT ?= $(abspath ../build/frameworks)
C_FRAMEWORKS := CoreFoundation AudioToolbox AudioUnit CoreAudio CoreAudioTypes CoreMIDI IOKit OpenAL Security SystemConfiguration
OBJC_FRAMEWORKS := Foundation AppKit CoreData Cocoa
OPTIONAL_FRAMEWORKS := CoreServices ApplicationServices CoreGraphics CoreVideo CoreMedia AVFoundation QuartzCore
SUPPORTED := $(C_FRAMEWORKS) $(OBJC_FRAMEWORKS) $(OPTIONAL_FRAMEWORKS)
FRAMEWORKS ?= $(C_FRAMEWORKS)
TESTS := $(addprefix test-,$(C_FRAMEWORKS))
OBJC_TESTS := test-Foundation test-Foundation-modules test-Cocoa test-Cocoa-modules
OPTIONAL_TESTS := $(addprefix test-,$(OPTIONAL_FRAMEWORKS))
PYTHON ?= python3

.PHONY: install stage prepare test test-objc check-test-tools $(SUPPORTED) $(TESTS) $(OBJC_TESTS) $(OPTIONAL_TESTS)

install:
	@set -eu; \
		test -n "$(strip $(FRAMEWORKS))" && test -z "$(filter-out $(SUPPORTED),$(FRAMEWORKS))" \
			|| { echo "Select frameworks from $(SUPPORTED)." >&2; exit 1; }; \
		test -n "$(OUT)" && test ! -e "$(OUT)" && test ! -L "$(OUT)" \
			|| { echo "Set OUT to a new directory." >&2; exit 1; }; \
		mkdir -p "$(dir $(abspath $(OUT)))"; \
		stage=$$(mktemp -d "$(dir $(abspath $(OUT))).frameworks.XXXXXX"); \
		trap 'rm -rf -- "$$stage"' EXIT; \
		$(MAKE) stage STAGE="$$stage"; \
		test ! -e "$(OUT)" && test ! -L "$(OUT)"; \
		mv "$$stage" "$(OUT)"

stage: $(FRAMEWORKS)

prepare: prepare-CF prepare-IOAudioFamily prepare-OpenAL prepare-Security prepare-configd

include common.mk
include $(addsuffix /Makefile,$(SUPPORTED))

test: $(TESTS)

test-objc: $(OBJC_TESTS)

$(TESTS) $(OBJC_TESTS) $(OPTIONAL_TESTS): check-test-tools

check-test-tools:
	@test -x "$(CLANG)" && test -n "$(SDK)" && test -d "$(SDK)/System/Library/Frameworks" \
		|| { echo "Set CLANG and SDK to the pinned compiler and composed SDK." >&2; exit 1; }
