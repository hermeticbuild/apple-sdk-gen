ifeq ($(SDK),macosx26.5)
.PHONY: stage-xpc-type
stage: stage-xpc-type
stage-xpc-type:
	mkdir -p "$(STAGE)/xpc/dst/usr/include/xpc"
	install -m 644 components/xpc/_xpc_object.h "$(STAGE)/xpc/dst/usr/include/xpc/"
	$(call header-record,xpc,usr/include/xpc/_xpc_object.h,derived:components/xpc/_xpc_object.h,components/xpc/Makefile,install the XPC object type required by Security,components/xpc/_xpc_object.h components/xpc/README.md)
endif
