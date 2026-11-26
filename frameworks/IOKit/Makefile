# IOAudioFamily-740.1
IOKIT_COMMIT := 6fdf514055a9868fe20e4dc3845b78dfa5e27110

.PHONY: prepare-IOAudioFamily
prepare-IOAudioFamily:
	$(call prepare-source,IOAudioFamily,$(IOKIT_COMMIT))

IOKit: require-stage
	mkdir -p "$(STAGE)/IOKit.framework/Headers/audio"
	git -C "$(SOURCE_ROOT)/IOAudioFamily" show "$(IOKIT_COMMIT):IOAudioTypes.h" \
		> "$(STAGE)/IOKit.framework/Headers/audio/IOAudioTypes.h"
	$(call write-tbd,IOKit,IOKit/exports.list)

test-IOKit:
	$(call test-framework-headers,IOKit)
