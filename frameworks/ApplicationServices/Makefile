APPLICATION_SERVICES_STAGE = $(STAGE)/ApplicationServices.framework

ApplicationServices: require-stage CoreServices
	$(call stage-framework-headers,ApplicationServices)
	mkdir -p "$(APPLICATION_SERVICES_STAGE)/Versions/A"
	install -m 644 ApplicationServices/ApplicationServices.tbd "$(APPLICATION_SERVICES_STAGE)/Versions/A/ApplicationServices.tbd"
	ln -s Versions/A/ApplicationServices.tbd "$(APPLICATION_SERVICES_STAGE)/ApplicationServices.tbd"

test-ApplicationServices:
	$(call test-sdk-link,ApplicationServices/test.m,-framework AppKit -framework CoreFoundation,-Wno-deprecated-declarations)
