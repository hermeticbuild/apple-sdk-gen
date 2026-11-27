#import <Network/Network.h>

int main(void) {
    nw_endpoint_t endpoint = nw_endpoint_create_host("localhost", "443");
    return !endpoint || nw_endpoint_get_port(endpoint) != 443;
}
