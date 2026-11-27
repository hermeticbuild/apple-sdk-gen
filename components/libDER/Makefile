ifeq ($(SDK),macosx26.5)
.PHONY: stage-libDER
stage: stage-libDER
stage-libDER:
	$(call copy-headers,libDER,libDER,sources/xnu/EXTERNAL_HEADERS/libDER/DERItem.h sources/xnu/EXTERNAL_HEADERS/libDER/libDER_config.h)
endif
