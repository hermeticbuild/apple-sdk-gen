#include <dns_sd.h>
#include <string.h>

int main(void) {
    char full_name[kDNSServiceMaxDomainName];
    DNSServiceErrorType error =
        DNSServiceConstructFullName(full_name, "probe", "_http._tcp", "local.");
    return error != kDNSServiceErr_NoError || strcmp(full_name, "probe._http._tcp.local.") != 0;
}
