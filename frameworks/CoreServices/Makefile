CORE_SERVICES_STAGE = $(STAGE)/CoreServices.framework
LAUNCH_SERVICES_PARENT = $(CORE_SERVICES_STAGE)/Versions/A/Frameworks
LAUNCH_SERVICES_STAGE = $(LAUNCH_SERVICES_PARENT)/LaunchServices.framework
LAUNCH_SERVICES_INSTALL_NAME := /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/LaunchServices
LLVM_READTAPI ?= $(dir $(CLANG))llvm-readtapi

CoreServices: require-stage CoreFoundation-versioned-tbd
	$(call stage-framework-headers,CoreServices)
	mkdir -p "$(LAUNCH_SERVICES_STAGE)/Headers" "$(LAUNCH_SERVICES_STAGE)/Versions/A"
	install -m 644 CoreServices/LaunchServices/*.h "$(LAUNCH_SERVICES_STAGE)/Headers/"
	ln -s ../Versions/A/Frameworks/LaunchServices.framework/Headers/LaunchServices.h "$(CORE_SERVICES_STAGE)/Headers/LaunchServices.h"
	ln -s ../Versions/A/Frameworks/LaunchServices.framework/Headers/UTType.h "$(CORE_SERVICES_STAGE)/Headers/UTType.h"
	$(call installapi,-iframework"$(STAGE)" -iframework"$(LAUNCH_SERVICES_PARENT)" --filetype=tbd-v4 \
		-install_name "$(LAUNCH_SERVICES_INSTALL_NAME)" \
		-extra-public-header "$(LAUNCH_SERVICES_STAGE)/Headers",$(LAUNCH_SERVICES_STAGE)/Versions/A/LaunchServices.tbd)
	test -s "$(LAUNCH_SERVICES_STAGE)/Versions/A/LaunchServices.tbd"
	ln -s Versions/A/LaunchServices.tbd "$(LAUNCH_SERVICES_STAGE)/LaunchServices.tbd"
	install -m 644 CoreServices/CoreServices.tbd "$(CORE_SERVICES_STAGE)/Versions/A/CoreServices.tbd"
	$(if $(CORE_SERVICES_TBD),$(merge-core-services-tbd))
	ln -s Versions/A/CoreServices.tbd "$(CORE_SERVICES_STAGE)/CoreServices.tbd"

define merge-core-services-tbd
@set -eu; \
	work=$$(mktemp -d "$${TMPDIR:-/tmp}/core-services-tbd.XXXXXX"); \
	trap 'rm -rf -- "$$work"' EXIT; \
	sed "/^install-name:/s|/CoreServices.framework/CoreServices'|/CoreServices.framework/Versions/A/CoreServices'|" \
		"$(CORE_SERVICES_TBD)" > "$$work/generated.tbd"; \
	"$(LLVM_READTAPI)" -merge --filetype=tbd-v4 "$$work/generated.tbd" \
		"$(CORE_SERVICES_STAGE)/Versions/A/CoreServices.tbd" -o "$$work/merged.tbd"; \
	install -m 644 "$$work/merged.tbd" "$(CORE_SERVICES_STAGE)/Versions/A/CoreServices.tbd"
endef

test-CoreServices:
	$(call test-sdk-link,CoreServices/test.c,-framework CoreServices -framework CoreFoundation,-Wno-deprecated-declarations)
