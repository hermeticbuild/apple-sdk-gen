#include <os/log.h>

void review_os_log_error(os_log_t log, int status) {
  os_log_error(log, "failure: %d", status);
}
