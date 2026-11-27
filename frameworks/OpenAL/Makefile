# OpenAL-71
OPENAL_HEADERS = $(STAGE)/OpenAL.framework/Headers
OPENAL_EXPORTS = $(STAGE)/.openal-exports

OpenAL: require-stage
	mkdir -p "$(OPENAL_HEADERS)"
	git -C "$(SOURCE_ROOT)/OpenAL" show "HEAD:Source/OpenAL/al/al.h" > "$(OPENAL_HEADERS)/al.h"
	git -C "$(SOURCE_ROOT)/OpenAL" show "HEAD:Source/OpenAL/al/alc.h" > "$(OPENAL_HEADERS)/alc.h"
	awk -f OpenAL/exports.awk "$(OPENAL_HEADERS)/al.h" "$(OPENAL_HEADERS)/alc.h" > "$(OPENAL_EXPORTS)"
	$(call write-tbd,OpenAL,$(OPENAL_EXPORTS))
	rm "$(OPENAL_EXPORTS)"

test-OpenAL:
	$(call test-framework-link,OpenAL,-Wno-deprecated-declarations)
