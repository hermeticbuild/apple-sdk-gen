#include <curl/curl.h>
#include <stdio.h>

int main(void) {
    CURLcode status = curl_global_init(CURL_GLOBAL_DEFAULT);
    if (status != CURLE_OK) {
        fprintf(stderr, "curl_global_init: %s\n", curl_easy_strerror(status));
        return 1;
    }

    CURL *curl = curl_easy_init();
    int initialized = curl != NULL;
    int handles_ipv6 = (curl_version_info(CURLVERSION_NOW)->features & CURL_VERSION_IPV6) != 0;
    if (curl)
        curl_easy_cleanup(curl);
    else
        fputs("curl_easy_init failed\n", stderr);
    if (!handles_ipv6)
        fputs("The curl test requires IPv6 for macOS proxy initialization\n", stderr);

    curl_global_cleanup();
    return !(initialized && handles_ipv6);
}
