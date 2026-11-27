# Libm.xcodeproj/project.pbxproj Copy ARM phase.
libm_root = $(STAGE)/Libm/dst
libm_include = $(libm_root)/usr/include
libm_recipe = recipes/libm
libm_source = $(SOURCE_ROOT)/Libm/Source
libm_complex_patches = $(libm_recipe)/complex.patch
libm_math_patches = $(libm_recipe)/math.patch
ifeq ($(SDK),macosx26.5)
libm_complex_patches += $(libm_recipe)/complex-darwin-26.5.patch
libm_math_patches += $(libm_recipe)/math-binary16-26.5.patch
endif

.PHONY: stage-Libm
stage: stage-Libm
stage-Libm:
ifeq ($(SDK),macosx26.5)
	mkdir -p "$(libm_include)/architecture/arm"
	install -m 644 "$(libm_source)/ARM/math.h" "$(libm_include)/architecture/arm/"
	$(call apply-recipe-patch,$(libm_root),$(libm_recipe)/arm-math-fpclassify-26.5.patch)
	$(call header-record,Libm,usr/include/architecture/arm/math.h,derived:sources/Libm/Source/ARM/math.h,$(libm_recipe)/Makefile,inline the Apple binary64 classifier for macOS arm64 C,sources/Libm/Source/ARM/math.h sources/Libm/Source/ARM/fpclassify.c $(libm_recipe)/arm-math-fpclassify-26.5.patch)
else
	$(call copy-headers,Libm,architecture/arm,sources/Libm/Source/ARM/math.h,$(libm_recipe)/Makefile)
endif
	install -m 644 "$(libm_source)/complex.h" "$(libm_source)/math.h" "$(libm_source)/fenv.h" "$(libm_include)/"
	mkdir -p "$(libm_include)/architecture/arm64"
	install -m 644 "$(libm_recipe)/arm64_fenv.h" "$(libm_include)/architecture/arm64/fenv.h"
	@set -e; for patch_file in $(libm_complex_patches) $(libm_math_patches); do \
		$(call apply-recipe-patch,$(libm_root),$$patch_file); \
	done
	$(call apply-recipe-patch,$(libm_root),$(libm_recipe)/fenv-arm64.patch)
	$(call header-record,Libm,usr/include/complex.h,derived:sources/Libm/Source/complex.h,$(libm_recipe)/Makefile,arm64 selection and complex constructors,sources/Libm/Source/complex.h $(libm_complex_patches))
	$(call header-record,Libm,usr/include/math.h,derived:sources/Libm/Source/math.h,$(libm_recipe)/Makefile,arm64 selection and macOS math extensions,sources/Libm/Source/math.h sources/xnu/bsd/sys/cdefs.h $(libm_math_patches))
	$(call header-record,Libm,usr/include/fenv.h,derived:sources/Libm/Source/fenv.h,$(libm_recipe)/Makefile,arm64 fenv include selection,sources/Libm/Source/fenv.h $(libm_recipe)/fenv-arm64.patch)
	$(call header-record,Libm,usr/include/architecture/arm64/fenv.h,$(libm_recipe)/arm64_fenv.h,$(libm_recipe)/Makefile,local ABI declaration and FPSR exception flags,$(libm_recipe)/arm64_fenv.h sources/Libm/Source/ARM/fenv.h sources/xnu/osfmk/arm64/proc_reg.h)
