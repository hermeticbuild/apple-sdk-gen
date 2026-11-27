# xcodeconfig/{atomics,os,libplatform}.xcconfig establishes destinations.
# The pinned project does not include the corresponding header phase membership.
.PHONY: stage-libplatform
stage: stage-libplatform
stage-libplatform:
	$(call copy-headers,libplatform,libkern,sources/libplatform/include/libkern/OSAtomic.h \
		sources/libplatform/include/libkern/OSAtomicDeprecated.h \
		sources/libplatform/include/libkern/OSAtomicQueue.h \
		sources/libplatform/include/libkern/OSCacheControl.h \
		sources/libplatform/include/libkern/OSSpinLockDeprecated.h)
	$(call copy-headers,libplatform,os,sources/libplatform/include/os/lock.h sources/libplatform/include/os/os_sync_wait_on_address.h)
	$(call copy-headers,libplatform,.,sources/libplatform/include/setjmp.h sources/libplatform/include/ucontext.h)
	@# Retain the reviewed source headers at their matching SDK paths.
	$(call copy-headers,libplatform,os,sources/libplatform/include/os/security_config.h)
	$(call copy-headers,libplatform,.,sources/libplatform/include/timingsafe.h)
