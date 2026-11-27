# dyld.xcodeproj/project.pbxproj macOS publicHeaders and configs/libdyld.xcconfig.
# Own fixup-chains.h here because XNU lists its version only as an export.
dyld_headers_root = $(STAGE)/dyld/dst
dyld_header_source = sources/dyld/include/mach-o

.PHONY: stage-dyld
stage: stage-dyld
stage-dyld:
	$(call copy-headers,dyld,.,sources/dyld/include/dlfcn.h)
	$(call copy-headers,dyld,mach-o,sources/dyld/include/mach-o/utils.h sources/dyld/include/mach-o/fixup-chains.h)
	install -m 644 "$(SOURCE_ROOT)/dyld/include/mach-o/dyld.h" \
		"$(SOURCE_ROOT)/dyld/include/mach-o/dyld_images.h" "$(dyld_headers_root)/usr/include/mach-o/"
	$(call apply-recipe-patch,$(dyld_headers_root),recipes/dyld/dyld-availability.patch)
	$(call apply-recipe-patch,$(dyld_headers_root),recipes/dyld/dyld-images-includes.patch)
	$(call header-record,dyld,usr/include/mach-o/dyld.h,derived:$(dyld_header_source)/dyld.h,recipes/dyld/Makefile,guard missing ExclaveKit availability macro,$(dyld_header_source)/dyld.h recipes/dyld/dyld-availability.patch)
	$(call header-record,dyld,usr/include/mach-o/dyld_images.h,derived:$(dyld_header_source)/dyld_images.h,recipes/dyld/Makefile,add public dependency includes,$(dyld_header_source)/dyld_images.h recipes/dyld/dyld-images-includes.patch)
