# The probe needs the two compatibility copies from the phone-build CCFILES.
carbon_root = $(STAGE)/CarbonHeaders/dst
carbon_include = $(carbon_root)/usr/include
carbon_template = sources/CarbonHeaders/TargetConditionals.h

.PHONY: stage-CarbonHeaders
stage: stage-CarbonHeaders
stage-CarbonHeaders:
	mkdir -p "$(carbon_root)"
	env -i PATH="$$PATH" $(MAKE) -C "$(SOURCE_ROOT)/CarbonHeaders" installhdrs \
		DSTROOT="$(carbon_root)" RC_ARCHS="arm64"
	@# AvailabilityVersions supplies these public headers.
	rm "$(carbon_include)/Availability.h" "$(carbon_include)/AvailabilityInternal.h" \
		"$(carbon_include)/AvailabilityMacros.h"
ifeq ($(SDK),macosx26.5)
	$(call copy-headers,CarbonHeaders,.,sources/CarbonHeaders/ConditionalMacros.h)
	install -m 644 "$(SOURCE_ROOT)/CarbonHeaders/MacTypes.h" "$(carbon_include)/"
	$(call apply-recipe-patch,$(carbon_root),recipes/CarbonHeaders/assert-macros-26.5.patch)
	$(call apply-recipe-patch,$(carbon_root),recipes/CarbonHeaders/mac-types-26.5.patch)
	$(call header-record,CarbonHeaders,usr/include/AssertMacros.h,derived:sources/CarbonHeaders/AssertMacros.h,recipes/CarbonHeaders/Makefile,default short names off while retaining explicit opt-in,sources/CarbonHeaders/AssertMacros.h sources/CarbonHeaders/Makefile recipes/CarbonHeaders/assert-macros-26.5.patch)
	$(call header-record,CarbonHeaders,usr/include/MacTypes.h,derived:sources/CarbonHeaders/MacTypes.h,recipes/CarbonHeaders/Makefile,prototype the two no-argument callbacks,sources/CarbonHeaders/MacTypes.h recipes/CarbonHeaders/mac-types-26.5.patch)
else
	$(call copy-headers,CarbonHeaders,.,sources/CarbonHeaders/ConditionalMacros.h sources/CarbonHeaders/MacTypes.h)
	$(call record-installed,CarbonHeaders,recipes/CarbonHeaders/Makefile,usr/include/AssertMacros.h)
endif
	$(call apply-recipe-patch,$(carbon_root),recipes/CarbonHeaders/target-conditionals.patch)
	$(call header-record,CarbonHeaders,usr/include/TargetConditionals.h,derived:$(carbon_template),recipes/CarbonHeaders/Makefile,Apple public header install and add architecture and ABI aliases,$(carbon_template) sources/CarbonHeaders/Makefile recipes/CarbonHeaders/target-conditionals.patch recipes/CarbonHeaders/macos-abi.md)
