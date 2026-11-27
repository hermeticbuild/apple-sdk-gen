
Security: require-stage
	@set -eu; \
		headers="$(STAGE)/Security.framework/Headers"; \
		mkdir -p "$$headers"; \
		while IFS= read -r source; do \
			git -C "$(SOURCE_ROOT)/Security" show "HEAD:$$source" > "$$headers/$${source##*/}"; \
		done < Security/headers.list
	patch -s -f -F 0 -V none -p1 -d "$(STAGE)/Security.framework" < Security/xpc-object-type.patch

test-Security:
	$(call test-framework-headers,Security)
