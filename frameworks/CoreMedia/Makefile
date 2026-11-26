CORE_MEDIA_STAGE = $(STAGE)/CoreMedia.framework

CoreMedia: require-stage CoreVideo
	$(call stage-framework-headers,CoreMedia,CMTime CMTimeRange CMFormatDescription CMSampleBuffer)
	$(call installapi,-F "$(STAGE)" \
		-install_name /System/Library/Frameworks/CoreMedia.framework/Versions/A/CoreMedia \
		-extra-public-header "$(CORE_MEDIA_STAGE)/Headers/CoreMedia.h",$(CORE_MEDIA_STAGE)/CoreMedia.tbd)
	mkdir -p "$(CORE_MEDIA_STAGE)/Versions/A"
	ln -s ../../CoreMedia.tbd "$(CORE_MEDIA_STAGE)/Versions/A/CoreMedia.tbd"

test-CoreMedia:
	$(call test-framework-link,CoreMedia)
