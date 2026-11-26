CoreAudio: require-stage
	$(call stage-local-framework,CoreAudio,CoreAudio/exports.list)
	$(if $(GENERATED_FRAMEWORKS),$(call merge-generated-stub,CoreAudio))

test-CoreAudio:
	$(call test-framework-link,CoreAudio)
