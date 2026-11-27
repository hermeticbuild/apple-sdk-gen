#include <asl.h>
#include <checkint.h>
#include <notify.h>
#include <notify_keys.h>
#include <os/log.h>
#include <os/security_config.h>
#include <pthread/introspection.h>
#include <removefile.h>
#include <string.h>
#include <sys/syscall.h>
#include <timingsafe.h>

_Static_assert(ASL_LEVEL_NOTICE == 5, "unexpected ASL notice level");
_Static_assert(sizeof(aslmsg) == sizeof(void *), "unexpected aslmsg ABI");
_Static_assert(SYS_getpid == 20, "unexpected getpid syscall number");
_Static_assert(PTHREAD_INTROSPECTION_THREAD_CREATE == 1, "unexpected pthread event");

void log_test_message(void) {
    os_log_error(OS_LOG_DEFAULT, "%{public}s", "log fixture");
}
