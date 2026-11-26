CORE_GRAPHICS_STAGE = $(STAGE)/CoreGraphics.framework

CoreGraphics: require-stage
	@test -f "$(COREGRAPHICS_FRAMEWORK)/Headers/CoreGraphics.h" || { echo "Set COREGRAPHICS_FRAMEWORK to the generated 26.5 bundle." >&2; exit 1; }
	cp -RP "$(COREGRAPHICS_FRAMEWORK)" "$(CORE_GRAPHICS_STAGE)"
	install -m 644 CoreGraphics/Headers/CGGeometry.h "$(CORE_GRAPHICS_STAGE)/Headers/CGGeometry.h"
	patch -s -f -F 0 -V none -p1 -d "$(CORE_GRAPHICS_STAGE)" < CoreGraphics/geometry-header.patch

test-CoreGraphics:
	@set -eu; \
		resource=$$("$(CLANG)" --no-default-config -print-resource-dir); \
		for cpu in $(SDK_TEST_ARCHS); do \
			$(test-clang) -fsyntax-only CoreGraphics/test.c; \
			$(test-clang) -fsyntax-only -DGEOMETRY_FIRST CoreGraphics/test.c; \
			echo "$$cpu CoreGraphics geometry include orders passed"; \
		done
