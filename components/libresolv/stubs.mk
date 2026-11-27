.DEFAULT_GOAL := install

include frameworks/common.mk

PYTHON ?= python3
SOURCE_ROOT ?= $(CURDIR)/build/inputs/sources/$(SDK)
# The public header uses the built-in libSystem _res compatibility data
# below 15.4. Scan at 15.4 so it is not declared as a libresolv export.
# TBD v4 carries no deployment floor. Older clients bind _res via libSystem.
INSTALLAPI_MIN := 15.4

.PHONY: install stage
install:
	@test -n "$(strip $(SDK))" || { echo "Pass an SDK lock name, for example SDK=macosx26.5." >&2; exit 1; }
	"$(PYTHON)" -m tools.fetch_sources --verify --lock locks/$(SDK).json \
		--dest "$(abspath $(SOURCE_ROOT))"
	@cmp -s "locks/$(SDK).json" "$(C_INSTALL)/source-lock.json" \
		|| { echo "C_INSTALL was not built with the $(SDK) source lock." >&2; exit 1; }
	@set -eu; \
		test -n "$(OUT)" && test ! -e "$(OUT)" && test ! -L "$(OUT)" \
			|| { echo "Set OUT to a new directory." >&2; exit 1; }; \
		mkdir -p "$(dir $(abspath $(OUT)))"; \
		stage=$$(mktemp -d "$(dir $(abspath $(OUT))).resolver.XXXXXX"); \
		trap 'rm -rf -- "$$stage"' EXIT; \
		$(MAKE) -f components/libresolv/stubs.mk stage STAGE="$$stage"; \
		test ! -e "$(OUT)" && test ! -L "$(OUT)"; \
		mv "$$stage" "$(OUT)"

stage: require-stage
	mkdir -p "$(STAGE)/usr/lib"
	$(call installapi,--filetype=tbd-v4 -fapplication-extension -install_name /usr/lib/libresolv.9.dylib -D__BIND_INSTALLAPI \
		$(foreach header,dns.h dns_util.h nameser.h resolv.h,-extra-public-header "$(C_INSTALL)/usr/include/$(header)") \
		-extra-public-header "$(SOURCE_ROOT)/libresolv/installapi.h" \
		-extra-private-header "$(SOURCE_ROOT)/libresolv/dns_private.h",$(STAGE)/usr/lib/libresolv.9.tbd)
	ln -s libresolv.9.tbd "$(STAGE)/usr/lib/libresolv.tbd"
