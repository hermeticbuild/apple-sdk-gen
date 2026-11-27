xnu_source := $(realpath $(SOURCE_ROOT)/xnu)
xnu_stage := $(abspath $(STAGE)/xnu)
xnu_work := $(xnu_stage)/work
xnu_dst := $(xnu_stage)/dst
xnu_leaf := $(abspath recipes/xnu/install.mk)
xnu_unifdef := /usr/bin/unifdef

# Keep the shipping scope here; the headers and their destination come from XNU.
xnu_mi := bsd/sys bsd/sys/_types bsd/machine bsd/uuid bsd/net \
	libkern/libkern bsd/netinet bsd/netinet6 bsd/bsm libkern/os \
	osfmk/mach osfmk/mach/machine osfmk/mach_debug
xnu_md := bsd/arm osfmk/arm libkern/libkern/arm osfmk/mach/arm

# The older public Make pin omits two visionOS platform names even though
# sys/cdefs.h uses them. Preserve the existing ordinary macOS output.
xnu_platform_exclusions := $(if $(filter macosx26.0,$(SDK)),XNU_PLATFORM_XROS XNU_PLATFORM_XRSimulator)

define xnu-install-public
mkdir -p "$(xnu_work)/$(1)"; \
$(MAKE) --no-print-directory -rR -C "$(xnu_work)/$(1)" -f "$(xnu_leaf)" install-public \
	SRCROOT="$(xnu_source)" SOURCE="$(xnu_source)/$(1)" KIND="$(2)" ONLY="$(3)" \
	SDKVERSION="$(patsubst macosx%,%,$(SDK))" DSTROOT="$(xnu_dst)" \
	UNIFDEF="$(xnu_unifdef)" RECORDS="$(xnu_stage)/records" \
	EXTRA_PLATFORM_EXCLUSIONS="$(xnu_platform_exclusions)" FLAGS_OUT="$(4)"
endef

.PHONY: stage-xnu
stage: stage-xnu
stage-xnu: stage-AvailabilityVersions
	mkdir -p "$(xnu_work)"
	@$(call xnu-install-public,bsd/sys,MI,,$(xnu_work)/public-flags)
	@set -e; for component in $(filter-out bsd/sys,$(xnu_mi)); do \
		$(call xnu-install-public,$$component,MI); \
	done
	@set -e; for component in $(xnu_md); do \
		$(call xnu-install-public,$$component,MD); \
	done
	@$(call xnu-install-public,osfmk/device,MI,device_types.h)
	@$(call xnu-install-public,osfmk/mach/arm64,MD_GEN,asm.h)
	/bin/sh recipes/xnu/install-libsyscall.sh "$(xnu_stage)" "$(xnu_unifdef)"
	mkdir -p "$(xnu_work)/syscall" "$(xnu_work)/availability-sdk/usr/local/libexec"
	"$(xnu_unifdef)" -x2 "$(xnu_source)/bsd/kern/syscalls.master" > "$(xnu_work)/syscall/bsd.syscalls.master"
	(cd "$(xnu_work)/syscall" && /bin/sh "$(xnu_source)/bsd/kern/makesyscalls.sh" bsd.syscalls.master header > /dev/null)
	"$(xnu_unifdef)" -x2 $$(cat "$(xnu_work)/public-flags") "$(xnu_work)/syscall/syscall.h" > "$(xnu_dst)/usr/include/sys/syscall.h"
	ln -s "$(abspath $(availability_build_source))/availability" "$(xnu_work)/availability-sdk/usr/local/libexec/availability.pl"
	ln -s "$(abspath $(availability_build_source))/availability.dsl" "$(xnu_work)/availability-sdk/usr/local/libexec/availability.dsl"
	/bin/bash "$(xnu_source)/bsd/sys/make_symbol_aliasing.sh" "$(xnu_work)/availability-sdk" "$(xnu_dst)/usr/include/sys/_symbol_aliasing.h"
	/bin/sh "$(xnu_source)/bsd/sys/make_posix_availability.sh" "$(xnu_dst)/usr/include/sys/_posix_availability.h"
	$(call header-record,xnu,usr/include/sys/syscall.h,generated:sources/xnu/bsd/kern/makesyscalls.sh,bsd/sys/Makefile:INSTALL_MI_GEN_LIST,XNU syscall header generator and macOS public unifdef,sources/xnu/bsd/kern/syscalls.master sources/xnu/bsd/kern/makesyscalls.sh sources/xnu/bsd/sys/Makefile sources/xnu/makedefs/MakeInc.cmd sources/xnu/makedefs/MakeInc.rule sources/xnu/makedefs/MakeInc.def)
	$(call header-record,xnu,usr/include/sys/_symbol_aliasing.h,generated:sources/xnu/bsd/sys/make_symbol_aliasing.sh,bsd/sys/Makefile:INSTALL_MI_GEN_LIST,XNU public header generator,sources/xnu/bsd/sys/Makefile sources/xnu/bsd/sys/make_symbol_aliasing.sh sources/AvailabilityVersions/availability sources/AvailabilityVersions/availability.dsl $(availability_supplement))
	$(call header-record,xnu,usr/include/sys/_posix_availability.h,generated:sources/xnu/bsd/sys/make_posix_availability.sh,bsd/sys/Makefile:INSTALL_MI_GEN_LIST,XNU public header generator,sources/xnu/bsd/sys/Makefile sources/xnu/bsd/sys/make_posix_availability.sh)

.PHONY: mig-arm64
mig-arm64: pre-mig
	/bin/sh recipes/xnu/mig.sh "$(MIG)" "$(CLANG)" "$(STAGE)/pre-mig" "$(STAGE)/$@"
