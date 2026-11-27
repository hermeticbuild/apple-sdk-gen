# IOAudioFamily-740.1

IOKit: require-stage
	mkdir -p "$(STAGE)/IOKit.framework/Headers/audio"
	git -C "$(SOURCE_ROOT)/IOAudioFamily" show "HEAD:IOAudioTypes.h" \
		> "$(STAGE)/IOKit.framework/Headers/audio/IOAudioTypes.h"
	$(call write-tbd,IOKit,IOKit/exports.list)

test-IOKit:
	$(call test-framework-headers,IOKit)
