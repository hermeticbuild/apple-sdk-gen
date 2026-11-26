QUARTZ_CORE_STAGE = $(STAGE)/QuartzCore.framework

QuartzCore: require-stage Foundation
	$(call stage-framework-headers,QuartzCore,CALayer)
	$(call installapi,$(objc-installapi) \
		-install_name /System/Library/Frameworks/QuartzCore.framework/Versions/A/QuartzCore \
		-extra-public-header "$(QUARTZ_CORE_STAGE)/Headers/QuartzCore.h",$(QUARTZ_CORE_STAGE)/QuartzCore.tbd,objective-c)
	mkdir -p "$(QUARTZ_CORE_STAGE)/Versions/A"
	ln -s ../../QuartzCore.tbd "$(QUARTZ_CORE_STAGE)/Versions/A/QuartzCore.tbd"

test-QuartzCore:
	$(call test-sdk-link,QuartzCore/test.m,-framework QuartzCore -framework Foundation -lobjc,-fobjc-arc)
