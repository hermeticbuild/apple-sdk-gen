# libdispatch.xcodeproj public Headers, Install Headers, and Postprocess Headers.
dispatch_root = $(STAGE)/libdispatch/dst
dispatch_headers = base.h block.h data.h dispatch.h dispatch_swift_shims.h group.h io.h \
	object.h once.h queue.h semaphore.h source.h time.h workloop.h
dispatch_os_headers = object.h workgroup.h workgroup_base.h workgroup_interval.h \
	workgroup_object.h workgroup_parallel.h clock.h
dispatch_os_private = object_private.h voucher_private.h voucher_activity_private.h \
	workgroup_private.h workgroup_object_private.h workgroup_interval_private.h eventlink_private.h
dispatch_filter = -U__DISPATCH_BUILDING_DISPATCH__ -U__linux__ -DTARGET_OS_WIN32=0 -U__ANDROID__

.PHONY: stage-libdispatch
stage: stage-libdispatch
stage-libdispatch:
	$(call copy-headers,libdispatch,dispatch,$(addprefix sources/libdispatch/dispatch/,$(dispatch_headers)))
	@# BlocksRuntime's CMake install is non-Darwin. Retain the explicit compatibility copy.
ifeq ($(SDK),macosx26.5)
	install -m 644 "$(SOURCE_ROOT)/libdispatch/src/BlocksRuntime/Block.h" "$(dispatch_root)/usr/include/"
	$(call apply-recipe-patch,$(dispatch_root),recipes/libdispatch/block-bounds.patch)
	$(call header-record,libdispatch,usr/include/Block.h,derived:sources/libdispatch/src/BlocksRuntime/Block.h,recipes/libdispatch/Makefile,annotate block copy and release for Clang bounds checking,sources/libdispatch/src/BlocksRuntime/Block.h recipes/libdispatch/Makefile recipes/libdispatch/block-bounds.patch recipes/libdispatch/block-bounds.md)
else
	$(call copy-headers,libdispatch,.,sources/libdispatch/src/BlocksRuntime/Block.h)
endif
	@set --; for header in $(dispatch_os_headers) $(dispatch_os_private); do \
		set -- "$$@" "$(SOURCE_ROOT)/libdispatch/os/$$header"; done; \
		env -i PATH="$$PATH" DEPLOYMENT_LOCATION=YES DSTROOT="$(dispatch_root)" \
			OS_PUBLIC_HEADERS_FOLDER_PATH=/usr/include/os \
			OS_PRIVATE_HEADERS_FOLDER_PATH=/usr/local/include/os \
			SCRIPT_INPUT_FILE_1="$$1" SCRIPT_INPUT_FILE_2="$$2" SCRIPT_INPUT_FILE_3="$$3" \
			SCRIPT_INPUT_FILE_4="$$4" SCRIPT_INPUT_FILE_5="$$5" SCRIPT_INPUT_FILE_6="$$6" \
			SCRIPT_INPUT_FILE_7="$$7" SCRIPT_INPUT_FILE_8="$$8" SCRIPT_INPUT_FILE_9="$$9" \
			SCRIPT_INPUT_FILE_10="$${10}" SCRIPT_INPUT_FILE_11="$${11}" SCRIPT_INPUT_FILE_12="$${12}" \
			SCRIPT_INPUT_FILE_13="$${13}" SCRIPT_INPUT_FILE_14="$${14}" \
			/bin/bash -e "$(SOURCE_ROOT)/libdispatch/xcodescripts/install-headers.sh"
	@# Apply the public subset of the deployment postprocessing phase.
	@set -e; for name in workgroup_object.h workgroup_interval.h workgroup_parallel.h; do \
		file="$(dispatch_root)/usr/include/os/$$name"; \
		unifdef $(dispatch_filter) -o "$$file" "$$file" || test "$$?" -eq 1; \
	done
	$(call record-installed,libdispatch,recipes/libdispatch/Makefile,usr/include/os)
