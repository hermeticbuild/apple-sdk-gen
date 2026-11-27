# Keep the Mach-O format declaration used by the C probe.
# Apple's apple-xbs-support/libunwind.mk skips installhdrs.
.PHONY: stage-libunwind
stage: stage-libunwind
stage-libunwind:
	$(call copy-headers,libunwind,mach-o,sources/libunwind/libunwind/include/mach-o/compact_unwind_encoding.h)
