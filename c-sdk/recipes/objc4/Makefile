# Nine public runtime headers qualified for Clang and compiler-rt.
# objc.xcodeproj/project.pbxproj installs these under usr/include/objc.
objc4_public_headers := NSObjCRuntime.h NSObject.h message.h objc-api.h objc-auto.h \
	objc-exception.h objc-sync.h objc.h runtime.h

.PHONY: stage-objc4
stage-objc4:
	$(call copy-headers,objc4,objc,$(addprefix sources/objc4/runtime/,$(objc4_public_headers)),sources/objc4/objc.xcodeproj/project.pbxproj)
