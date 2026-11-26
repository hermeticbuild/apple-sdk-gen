CORE_VIDEO_STAGE = $(STAGE)/CoreVideo.framework

CoreVideo: require-stage CoreFoundation-versioned-tbd
	$(call stage-framework-headers,CoreVideo,CVBase CVBuffer CVImageBuffer CVPixelBuffer CVPixelBufferPool CVReturn)
	$(call installapi,-F "$(STAGE)" \
		-install_name /System/Library/Frameworks/CoreVideo.framework/Versions/A/CoreVideo \
		-extra-public-header "$(CORE_VIDEO_STAGE)/Headers/CoreVideo.h",$(CORE_VIDEO_STAGE)/CoreVideo.tbd)
	mkdir -p "$(CORE_VIDEO_STAGE)/Versions/A"
	ln -s ../../CoreVideo.tbd "$(CORE_VIDEO_STAGE)/Versions/A/CoreVideo.tbd"

test-CoreVideo:
	$(call test-framework-link,CoreVideo,-framework CoreFoundation)
