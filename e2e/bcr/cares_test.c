#include <ares.h>
#include <stdio.h>

int main(void) {
    int status = ares_library_init(ARES_LIB_INIT_ALL);
    if (status != ARES_SUCCESS) {
        fprintf(stderr, "ares_library_init: %s\n", ares_strerror(status));
        return 1;
    }

    ares_channel_t *channel = NULL;
    status = ares_init_options(&channel, NULL, 0);
    if (status == ARES_SUCCESS)
        ares_destroy(channel);
    else
        fprintf(stderr, "ares_init_options: %s\n", ares_strerror(status));

    ares_library_cleanup();
    return status != ARES_SUCCESS;
}
