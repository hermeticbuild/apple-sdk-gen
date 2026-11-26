# OpenAL-71
OPENAL_COMMIT := f6f9a3c01868d07937a46425fe0ce555e3341bb2
OPENAL_HEADERS = $(STAGE)/OpenAL.framework/Headers
OPENAL_EXPORTS = $(STAGE)/.openal-exports

.PHONY: prepare-OpenAL
prepare-OpenAL:
	$(call prepare-source,OpenAL,$(OPENAL_COMMIT))

OpenAL: require-stage
	mkdir -p "$(OPENAL_HEADERS)"
	git -C "$(SOURCE_ROOT)/OpenAL" show "$(OPENAL_COMMIT):Source/OpenAL/al/al.h" > "$(OPENAL_HEADERS)/al.h"
	git -C "$(SOURCE_ROOT)/OpenAL" show "$(OPENAL_COMMIT):Source/OpenAL/al/alc.h" > "$(OPENAL_HEADERS)/alc.h"
	awk -f OpenAL/exports.awk "$(OPENAL_HEADERS)/al.h" "$(OPENAL_HEADERS)/alc.h" > "$(OPENAL_EXPORTS)"
	$(call write-tbd,OpenAL,$(OPENAL_EXPORTS))
	rm "$(OPENAL_EXPORTS)"

test-OpenAL:
	$(call test-framework-link,OpenAL,-Wno-deprecated-declarations)
