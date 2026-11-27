# mDNSPosix/Makefile installs this public DNS-SD header under include/.
.PHONY: stage-mDNSResponder
stage: stage-mDNSResponder
stage-mDNSResponder:
	$(call copy-headers,mDNSResponder,.,sources/mDNSResponder/mDNSShared/dns_sd.h,sources/mDNSResponder/mDNSPosix/Makefile)
