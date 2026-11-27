# Public headers from libresolv.xcodeproj. Apple's headers.sh aliases
# arpa/nameser.h to nameser.h. Ship the identical Apple source at both paths
# because the C header manifest records regular files.
.PHONY: stage-libresolv
stage: stage-libresolv
stage-libresolv:
	$(call copy-headers,libresolv,.,sources/libresolv/dns.h sources/libresolv/dns_util.h sources/libresolv/nameser.h sources/libresolv/resolv.h,sources/libresolv/libresolv.xcodeproj/project.pbxproj)
	$(call copy-headers,libresolv,arpa,sources/libresolv/nameser.h,sources/libresolv/xcodescripts/headers.sh)
