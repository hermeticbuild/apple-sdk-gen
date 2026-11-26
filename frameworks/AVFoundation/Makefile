AV_FOUNDATION_STAGE = $(STAGE)/AVFoundation.framework

AVFoundation: require-stage CoreMedia CoreGraphics Foundation
	$(call stage-framework-headers,AVFoundation,AVAsset AVAssetTrack AVAssetReader AVAssetReaderOutput AVAssetWriter AVAssetWriterInput AVCaptureDevice AVCaptureInput AVCaptureOutput AVCaptureSession AVCaptureVideoDataOutput AVMediaFormat AVVideoSettings)
	$(call installapi,$(objc-installapi) \
		-install_name /System/Library/Frameworks/AVFoundation.framework/Versions/A/AVFoundation \
		-extra-public-header "$(AV_FOUNDATION_STAGE)/Headers/AVFoundation.h",$(AV_FOUNDATION_STAGE)/AVFoundation.tbd,objective-c)
	mkdir -p "$(AV_FOUNDATION_STAGE)/Versions/A"
	ln -s ../../AVFoundation.tbd "$(AV_FOUNDATION_STAGE)/Versions/A/AVFoundation.tbd"

test-AVFoundation:
	$(call test-sdk-link,AVFoundation/test.m,-framework AVFoundation -framework CoreMedia -framework CoreVideo -framework Foundation -lobjc,-fobjc-arc)
