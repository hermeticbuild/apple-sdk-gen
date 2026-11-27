# cctools.xcodeproj/project.pbxproj macOS machinable header phases and
# xcode/macho_headers.xcconfig for architecture-specific relocation headers.
.PHONY: stage-cctools
stage: stage-cctools
stage-cctools:
	$(call copy-headers,cctools,mach-o,sources/cctools/include/mach-o/arch.h \
		sources/cctools/include/mach-o/fat.h \
		sources/cctools/include/mach-o/getsect.h \
		sources/cctools/include/mach-o/ldsyms.h \
		sources/cctools/include/mach-o/loader.h \
		sources/cctools/include/mach-o/nlist.h \
		sources/cctools/include/mach-o/ranlib.h \
		sources/cctools/include/mach-o/reloc.h \
		sources/cctools/include/mach-o/stab.h \
		sources/cctools/include/mach-o/swap.h)
	$(call copy-headers,cctools,mach-o/arm,sources/cctools/include/mach-o/arm/reloc.h)
	$(call copy-headers,cctools,mach-o/arm64,sources/cctools/include/mach-o/arm64/reloc.h)
