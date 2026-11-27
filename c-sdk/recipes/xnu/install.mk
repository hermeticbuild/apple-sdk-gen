# Run the pinned XNU leaf rules for one selected public header list.
# SOURCE and SRCROOT are absolute; Make runs from a fresh work directory.
.DEFAULT_GOAL := install-public
xnu_helpers := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
# XNU components export their own MakeInc paths, so override recursion.
override MakeInc_dir := /dev/null

# Do not discover an SDK or toolchain while evaluating XNU's rules.
override PLATFORM := MacOSX
override SDKROOT_RESOLVED := /
override HOST_SDKROOT_RESOLVED := /
override XCRUN := /usr/bin/false
override CC := /usr/bin/false
override INCDIR := usr/include
override INSTALL := /usr/bin/install
override INSTALL_FLAGS := -m 644
override DECOMMENT := /usr/bin/perl "$(xnu_helpers)decomment.pl"
override REPLACECONTENTS := /bin/sh "$(xnu_helpers)replacecontents.sh"
override PLATFORM_UNIFDEF_BLACKLIST_TOKENS_MacOSX += $(EXTRA_PLATFORM_EXCLUSIONS)

include $(SOURCE)/Makefile

public_list := INSTALL_$(KIND)_LIST
public_dir := $(INSTALL_$(firstword $(subst _, ,$(KIND)))_DIR)
public_headers := $(sort $(filter %.h,$($(public_list))))
ifneq ($(strip $(ONLY)),)
ifneq ($(filter-out $(public_headers),$(ONLY)),)
$(error $(SOURCE)/Makefile: $(ONLY) missing from $(public_list))
endif
public_headers := $(ONLY)
endif
ifeq ($(strip $(public_headers)),)
$(error $(SOURCE)/Makefile: empty public header selection for $(public_list))
endif
ifeq ($(strip $(public_dir)),)
$(error $(SOURCE)/Makefile: missing public header destination for $(public_list))
endif

component := $(patsubst $(SRCROOT)/%,%,$(SOURCE))
public_paths := $(addprefix $(INCDIR)/$(public_dir)/,$(public_headers))

.PHONY: install-public
# For the two generated asm.h targets, Make resolves the prerequisite via
# XNU's VPATH. Use that same resolved path in the provenance record.
install-public: $(if $(filter MD_GEN,$(KIND)),asm.h) $(addprefix $(DSTROOT)/,$(public_paths))
	@set -eu; \
	for path in $(public_paths); do \
		test -f "$(DSTROOT)/$$path" || continue; \
		input="$(component)/$${path#$(INCDIR)/$(public_dir)/}"; \
		if [ "$(KIND)" = MD_GEN ]; then \
			input="$(patsubst $(SRCROOT)/%,%,$(realpath $<))"; \
		fi; \
		printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
			"$$path" xnu "derived:sources/xnu/$$input" "$(component)/Makefile:$(public_list)" \
			"Apple XNU public header install" "sources/xnu/$$input" "sources/xnu/$(component)/Makefile" \
			sources/xnu/makedefs/MakeInc.cmd sources/xnu/makedefs/MakeInc.def sources/xnu/makedefs/MakeInc.rule \
			recipes/xnu/decomment.pl; \
	done >> "$(RECORDS)"
	$(if $(FLAGS_OUT),@printf '%s\n' '$(strip $(SINCFRAME_UNIFDEF))' > "$(FLAGS_OUT)")
