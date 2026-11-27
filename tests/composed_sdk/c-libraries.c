#include <sys/types.h>
#include <bsm/audit_record.h>
#include <iconv.h>
#include <netinet6/ipsec.h>
#include <zlib.h>

/* Keep a real link reference without changing system IPsec configuration. */
static __typeof__(&ipsec_set_policy) volatile ipsec_client = &ipsec_set_policy;

int main(void) {
    iconv_t converter = iconv_open("UTF-8", "UTF-8");
    int error = -1;
    if (converter == (iconv_t)-1 || iconv_close(converter) != 0)
        return 1;
    if (zlibVersion()[0] == '\0' || ipsec_client == 0)
        return 2;
    (void)au_bsm_to_errno(0, &error);
    return error != 0;
}
