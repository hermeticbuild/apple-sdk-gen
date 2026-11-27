# libpthread.xcodeproj public Headers, then Apple's system-header and alias scripts.
pthread_root = $(STAGE)/libpthread/dst
pthread_headers = introspection.h pthread.h pthread_impl.h pthread_spis.h qos.h sched.h

.PHONY: stage-libpthread
stage: stage-libpthread
stage-libpthread:
	$(call copy-headers,libpthread,pthread,$(addprefix sources/libpthread/include/pthread/,$(pthread_headers)))
	env -i PATH="$$PATH" ACTION=installhdrs SRCROOT="$(SOURCE_ROOT)/libpthread" \
		DSTROOT="$(pthread_root)" COPY_HEADERS_UNIFDEF_FLAGS=-U__PTHREAD_BUILDING_PTHREAD__ \
		/bin/bash "$(SOURCE_ROOT)/libpthread/xcodescripts/install-sys-headers.sh"
	env -i PATH="$$PATH" ACTION=installhdrs DSTROOT="$(pthread_root)" \
		/bin/bash -e "$(SOURCE_ROOT)/libpthread/xcodescripts/install-symlinks.sh"
	$(call record-installed,libpthread,recipes/libpthread/Makefile,usr/include/sys)
	$(call record-installed,libpthread,recipes/libpthread/Makefile,usr/include/pthread.h)
	$(call record-installed,libpthread,recipes/libpthread/Makefile,usr/include/pthread_impl.h)
	$(call record-installed,libpthread,recipes/libpthread/Makefile,usr/include/pthread_spis.h)
	$(call record-installed,libpthread,recipes/libpthread/Makefile,usr/include/sched.h)
