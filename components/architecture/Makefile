.PHONY: stage-architecture
stage: stage-architecture
stage-architecture:
	mkdir -p "$(STAGE)/architecture/dst"
	env -i PATH="$$PATH" $(MAKE) -C "$(SOURCE_ROOT)/architecture" installhdrs \
		DSTROOT="$(STAGE)/architecture/dst" RC_ARCHS="arm64"
	$(call record-installed,architecture,sources/architecture/Makefile,usr/include)
