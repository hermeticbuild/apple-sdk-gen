.PHONY: stage-Libinfo
stage: stage-Libinfo
stage-Libinfo:
	mkdir -p "$(STAGE)/Libinfo/dst"
	cd "$(SOURCE_ROOT)/Libinfo" && env -i PATH="$$PATH" DSTROOT="$(STAGE)/Libinfo/dst" \
		PLATFORM_NAME=macosx ACTION=installhdrs \
		INSTALL_OWNER="$$(id -un)" INSTALL_GROUP="$$(id -gn)" \
		/bin/bash -e xcodescripts/install_files.sh
	$(call record-installed,Libinfo,sources/Libinfo/xcodescripts/install_files.sh,usr/include)
