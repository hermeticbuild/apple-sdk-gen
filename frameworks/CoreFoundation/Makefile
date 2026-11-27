CF_STAGE = $(STAGE)/CoreFoundation.framework

CoreFoundation: require-stage
	@set -eu; \
		mkdir -p "$(CF_STAGE)/Headers"; \
		while IFS= read -r header; do \
			git -C "$(SOURCE_ROOT)/CF" show "HEAD:$$header" > "$(CF_STAGE)/Headers/$$header"; \
		done < CoreFoundation/headers.list
	patch -s -f -F 0 -V none -p1 -d "$(CF_STAGE)" < CoreFoundation/modern-c-api.patch
	patch -s -f -F 0 -V none -p1 -d "$(CF_STAGE)" < CoreFoundation/modern-framework-macros.patch
	patch -s -f -F 0 -V none -p1 -d "$(CF_STAGE)" < CoreFoundation/managed-preferences.patch
	$(call installapi,-F "$(STAGE)" --filetype=tbd-v5 -fapplication-extension \
		-install_name /System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation \
		-extra-public-header "$(CF_STAGE)/Headers" -extra-public-header "$(CURDIR)/CoreFoundation/installapi.h",$(CF_STAGE)/CoreFoundation.tbd)

.PHONY: CoreFoundation-versioned-tbd
CoreFoundation-versioned-tbd: CoreFoundation
	mkdir -p "$(CF_STAGE)/Versions/A"
	ln -s ../../CoreFoundation.tbd "$(CF_STAGE)/Versions/A/CoreFoundation.tbd"

test-CoreFoundation:
	$(call test-framework-link,CoreFoundation,$(application-extension-link))
