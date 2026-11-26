COCOA_SDK_GEN_COMMIT := 0d09d30194aad45f292d9759f49bb19b8aab069f

Cocoa: require-stage Foundation AppKit CoreData
	@set -eu; \
		test -n "$(SDK_GEN_SOURCE)" || { echo "Set SDK_GEN_SOURCE to a Git checkout with Cocoa PR #11." >&2; exit 1; }; \
		git -C "$(SDK_GEN_SOURCE)" cat-file -e '$(COCOA_SDK_GEN_COMMIT)^{commit}'; \
		temp=$$(mktemp -d "$${TMPDIR:-/tmp}/cocoa-recipe.XXXXXX"); \
		trap 'rm -rf -- "$$temp"' EXIT; \
		git -C "$(SDK_GEN_SOURCE)" archive '$(COCOA_SDK_GEN_COMMIT)' tools/apple_sdk_gen | tar -xf - -C "$$temp"; \
		PYTHONPATH="$$temp" "$(PYTHON)" -c 'from pathlib import Path; import sys; from tools.apple_sdk_gen.assembler.cocoa import assemble_cocoa; assemble_cocoa(Path(sys.argv[1]), ["arm64-macos"])' "$(STAGE)"
	patch -s -f -F 0 -V none -p1 -d "$(STAGE)/Cocoa.framework" < Cocoa/versioned-appkit.patch

test-Cocoa:
	$(call test-sdk-link,Cocoa/test.m,-fobjc-arc -framework Cocoa -lobjc)

test-Cocoa-modules:
	$(call test-objc-modules,Cocoa)
