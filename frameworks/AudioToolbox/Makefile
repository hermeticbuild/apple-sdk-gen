AudioToolbox: require-stage
	$(call stage-local-framework,AudioToolbox,AudioToolbox/exports.list)
	$(if $(GENERATED_FRAMEWORKS),$(call merge-generated-stub,AudioToolbox))

test-AudioToolbox:
	$(call test-framework-link,AudioToolbox)
