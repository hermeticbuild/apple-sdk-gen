ifeq ($(SDK),macosx26.5)
.PHONY: stage-xpc-type
stage: stage-xpc-type
stage-xpc-type:
	mkdir -p "$(STAGE)/xpc/dst/usr/include/xpc"
	install -m 644 recipes/xpc/_xpc_object.h "$(STAGE)/xpc/dst/usr/include/xpc/"
	$(call header-record,xpc,usr/include/xpc/_xpc_object.h,derived:recipes/xpc/_xpc_object.h,recipes/xpc/Makefile,install the XPC object type required by Security,recipes/xpc/_xpc_object.h recipes/xpc/README.md)
endif
