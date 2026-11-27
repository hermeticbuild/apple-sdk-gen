.PHONY: stage-Libc
stage: stage-Libc
stage-Libc:
	mkdir -p "$(STAGE)/Libc/dst" "$(STAGE)/Libc/derived"
	cd "$(SOURCE_ROOT)/Libc" && env -i PATH="$$PATH" SRCROOT="$$PWD" \
		DSTROOT="$(STAGE)/Libc/dst" DERIVED_FILES_DIR="$(STAGE)/Libc/derived" \
		ARCHS="arm64" RC_ARCHS="arm64" PLATFORM_NAME=macosx \
		VARIANT_PLATFORM_NAME=macosx DEPLOYMENT_LOCATION=YES \
		/bin/bash -e xcodescripts/headers.sh
	$(call record-installed,Libc,sources/Libc/xcodescripts/headers.sh,usr/include)
