# The project marks both headers Public. xcodeconfig/libnotify.xcconfig sets /usr/include.
.PHONY: stage-Libnotify
stage: stage-Libnotify
stage-Libnotify:
	$(call copy-headers,Libnotify,.,sources/Libnotify/notify.h \
		sources/Libnotify/notify_keys.h,sources/Libnotify/Libnotify.xcodeproj/project.pbxproj)
