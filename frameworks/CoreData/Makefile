CORE_DATA_STAGE = $(STAGE)/CoreData.framework

CoreData: require-stage Foundation
	@test -f "$(OBJC4_INSTALL)/usr/include/objc/NSObject.h" || { echo "Set OBJC4_INSTALL to the pinned objc4 installation." >&2; exit 1; }
	$(call stage-framework-headers,CoreData,NSEntityDescription NSManagedObjectModel)
	$(call installapi,$(objc-installapi) \
		-install_name /System/Library/Frameworks/CoreData.framework/CoreData \
		-extra-public-header "$(CORE_DATA_STAGE)/Headers/CoreData.h",$(CORE_DATA_STAGE)/CoreData.tbd,objective-c)
