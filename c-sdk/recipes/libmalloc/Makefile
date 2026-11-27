# libmalloc.xcodeproj/project.pbxproj public headers and xcodeconfig/libmalloc.xcconfig.
# The pinned xcodescripts/sanitise_headers.sh contains no transformations.
malloc_type_header = libmalloc/include/malloc/_malloc_type.h
malloc_type_dst = usr/include/malloc/_malloc_type.h

.PHONY: stage-libmalloc
stage: stage-libmalloc
stage-libmalloc:
	$(call copy-headers,libmalloc,malloc,sources/libmalloc/include/malloc/_malloc.h \
		sources/libmalloc/include/malloc/_platform.h \
		sources/libmalloc/include/malloc/_ptrcheck.h \
		sources/libmalloc/include/malloc/malloc.h)
ifeq ($(SDK),macosx26.5)
	install -m 644 "$(SOURCE_ROOT)/$(malloc_type_header)" "$(STAGE)/libmalloc/dst/$(malloc_type_dst)"
	$(call apply-recipe-patch,$(STAGE)/libmalloc/dst,recipes/libmalloc/malloc-type-backdeployment-26.5.patch)
	$(call header-record,libmalloc,$(malloc_type_dst),derived:sources/$(malloc_type_header),recipes/libmalloc/Makefile,select public SDK backdeployment branch,sources/$(malloc_type_header) sources/libmalloc/tests/malloc_type_backdeploy.c recipes/libmalloc/malloc-type-backdeployment-26.5.patch)
else
	$(call copy-headers,libmalloc,malloc,sources/$(malloc_type_header))
endif
