SC_STAGE = $(STAGE)/SystemConfiguration.framework

SystemConfiguration: require-stage CoreFoundation Security
	@set -eu; \
		mkdir -p "$(SC_STAGE)/Headers" "$(SC_STAGE)/Modules"; \
		while IFS= read -r header; do \
			git -C "$(SOURCE_ROOT)/configd" show "HEAD:SystemConfiguration.fproj/$$header" \
				> "$(SC_STAGE)/Headers/$$header"; \
		done < SystemConfiguration/headers.list; \
		git -C "$(SOURCE_ROOT)/configd" show "HEAD:SystemConfiguration.fproj/Modules/SystemConfiguration.modulemap" \
			> "$(SC_STAGE)/Modules/module.modulemap"
	patch -s -f -F 0 -V none -p1 -d "$(SC_STAGE)" < SystemConfiguration/authorization-header.patch
	$(call installapi,-iframework"$(STAGE)" --filetype=tbd-v5 -fapplication-extension \
		-install_name /System/Library/Frameworks/SystemConfiguration.framework/Versions/A/SystemConfiguration \
		-current_version 1405.120.5 -extra-public-header "$(SC_STAGE)/Headers",$(SC_STAGE)/SystemConfiguration.tbd)

test-SystemConfiguration:
	$(call test-framework-headers,SystemConfiguration,reachability.c)
	$(call test-framework-link,SystemConfiguration,-framework CoreFoundation $(application-extension-link))
