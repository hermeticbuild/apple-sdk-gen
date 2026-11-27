# The project marks both headers Public. xcodescripts/removefile.xcconfig sets /usr/include.
.PHONY: stage-removefile
stage: stage-removefile
stage-removefile:
	$(call copy-headers,removefile,.,sources/removefile/checkint.h \
		sources/removefile/removefile.h,sources/removefile/removefile.xcodeproj/project.pbxproj)
