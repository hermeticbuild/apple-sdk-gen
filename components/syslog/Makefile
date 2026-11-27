# syslog.xcodeproj marks asl.h public. libasl.xcconfig installs it to /usr/include.
.PHONY: stage-syslog
stage: stage-syslog
stage-syslog:
	$(call copy-headers,syslog,.,sources/syslog/libsystem_asl.tproj/include/asl.h)
