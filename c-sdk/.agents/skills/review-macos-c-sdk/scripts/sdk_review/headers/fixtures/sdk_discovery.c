// C coverage roots. Compile once as a whole and once per include, for both targets.
// Seed: https://codeberg.org/ziglang/zig/src/commit/6b0a1d8b426a9b60f999358d4b7f57aa0b231777/tools/macos-headers.c
// Zig seed differences: omit five objc/* roots (outside this C-only scope) and
// net/ipsec_offload.h (absent from macOS 26.5 SDK); add sandbox.h,
// TargetConditionals.h, and CoreFoundation/CoreFoundation.h.
// ucontext.h requires _XOPEN_SOURCE; _DARWIN_C_SOURCE retains Darwin extensions.
//
// Header-inclusion coverage (244 unique roots, not API conformance):
// Inventory editions are fixed here; newer C/POSIX editions are not counted.
//   ISO C11 (WG14 N1570, 7.1.2): 27/29; absent: threads.h, uchar.h.
//   ANSI C89 (subset of C11): 15/15.
//   POSIX.1-2017 Issue 7 (Base Definitions, Ch. 13): 79/82;
//     absent: mqueue.h, stropts.h, trace.h. 24 POSIX roots overlap C11.
//   macOS/BSD, frameworks, and other extensions: 162 additional roots.
// The five absent standard roots are absent from both the macOS 26.5 SDK and
// our pinned Clang resource headers; POSIX counts include optional facilities.
// See tools/sdk_review/README.md for how to report missing paths.
// Clang resource headers remain compiler-owned; the counts classify requested
// include names, irrespective of whether Clang or the sysroot provides them.
// LLVM libunwind headers are a separately pinned runtime layer and are checked
// in the restricted LLVM composition, outside this standalone C-root probe.
// ISO C11: https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf
// ANSI C89 / ISO C90: https://www.iso.org/standard/17782.html
// POSIX: https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/contents.html
#define _XOPEN_SOURCE 700
#define _DARWIN_C_SOURCE 1

// ISO C11: 27/29 roots (includes all 15 ANSI C89 headers).
// https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf
// https://www.iso.org/standard/17782.html
// Unseeded: threads.h (conditional C11 feature), uchar.h. Neither is in the
// macOS 26.5 SDK or pinned Clang resource directory.
#include <assert.h>
#include <complex.h>
#include <ctype.h>
#include <errno.h>
#include <fenv.h>
#include <float.h>
#include <inttypes.h>
#include <iso646.h>
#include <limits.h>
#include <locale.h>
#include <math.h>
#include <setjmp.h>
#include <signal.h>
#include <stdalign.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdnoreturn.h>
#include <string.h>
#include <tgmath.h>
#include <time.h>
#include <wchar.h>
#include <wctype.h>

// POSIX.1-2017 Issue 7: 55 additional roots; 24 also appear above (79/82).
// https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/contents.html
// Unseeded: mqueue.h, stropts.h, trace.h. All three are specified in Chapter
// 13 but absent from the macOS 26.5 SDK and pinned Clang resource directory.
#include <aio.h>
#include <arpa/inet.h>
#include <cpio.h>
#include <dirent.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <fmtmsg.h>
#include <fnmatch.h>
#include <ftw.h>
#include <glob.h>
#include <grp.h>
#include <iconv.h>
#include <langinfo.h>
#include <libgen.h>
#include <monetary.h>
#include <ndbm.h>
#include <net/if.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <nl_types.h>
#include <poll.h>
#include <pthread.h>
#include <pwd.h>
#include <regex.h>
#include <sched.h>
#include <search.h>
#include <semaphore.h>
#include <spawn.h>
#include <strings.h>
#include <sys/ipc.h>
#include <sys/mman.h>
#include <sys/msg.h>
#include <sys/resource.h>
#include <sys/select.h>
#include <sys/sem.h>
#include <sys/shm.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/time.h>
#include <sys/times.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <sys/un.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <syslog.h>
#include <tar.h>
#include <termios.h>
#include <ulimit.h>
#include <unistd.h>
#include <utime.h>
#include <utmpx.h>
#include <wordexp.h>

// macOS/BSD, frameworks, and other extensions: 155 roots.
// Zig seed: https://codeberg.org/ziglang/zig/src/commit/6b0a1d8b426a9b60f999358d4b7f57aa0b231777/tools/macos-headers.c
// Unseeded Zig roots: objc/NSObjCRuntime.h, objc/NSObject.h, objc/message.h,
// objc/objc-runtime.h, objc/objc.h (outside C-only scope); net/ipsec_offload.h
// (absent from macOS 26.5 SDK). Additional roots exercise Apple OSS public
// install manifests.
#include <AssertMacros.h>
#include <Block.h>
#include <CommonCrypto/CommonCrypto.h>
#include <CommonCrypto/CommonRandom.h>
#include <CoreFoundation/CoreFoundation.h>
#include <MacTypes.h>
#include <TargetConditionals.h>
#include <ar.h>
#include <asl.h>
#if defined(APPLE_C_PROBE_ARCHITECTURE_HEADERS)
// Independently compiled roots. Some architecture headers define overlapping
// assembler helpers; five more public paths fail even against Xcode 26.5 when
// individually included for one or both targets (see COVERAGE_GAPS.md).
#include <architecture/byte_order.h>
#include <architecture/arm/byte_order.h>
#endif
#include <atm/atm_types.h>
#include <arpa/nameser.h>
#include <bsm/audit_filter.h>
#include <bsm/audit_uevents.h>
#include <bsm/libbsm.h>
#include <checkint.h>
#include <copyfile.h>
#include <crt_externs.h>
#include <db.h>
#include <device/device_types.h>
#include <device/device_port.h>
#include <dns.h>
#include <dns_sd.h>
#include <dns_util.h>
#include <dispatch/dispatch.h>
#include <err.h>
#include <execinfo.h>
#include <fts.h>
#include <getopt.h>
#include <hfs/hfs_format.h>
#include <hfs/hfs_mount.h>
#include <hfs/hfs_unistr.h>
#include <ifaddrs.h>
#include <libkern/OSAtomic.h>
#include <libkern/OSAtomicQueue.h>
#include <libkern/OSByteOrder.h>
#include <libkern/OSCacheControl.h>
#include <libkern/OSDebug.h>
#include <libkern/OSKextLib.h>
#include <libkern/OSReturn.h>
#include <libkern/OSThermalNotification.h>
#include <libkern/OSTypes.h>
#include <libproc.h>
#if defined(APPLE_C_PROBE_PROVISIONAL_SOURCES)
// Compile these roots individually while their public Apple install rule
// remains unresolved. Probe success does not approve their provenance.
#include <libDER/DERItem.h>
#include <libDER/libDER_config.h>
#endif
#include <mach-o/arch.h>
#include <mach-o/arm/reloc.h>
#include <mach-o/arm64/reloc.h>
#include <mach-o/compact_unwind_encoding.h>
#include <mach-o/dyld.h>
#include <mach-o/dyld_images.h>
#include <mach-o/fat.h>
#include <mach-o/fixup-chains.h>
#include <mach-o/getsect.h>
#include <mach-o/ldsyms.h>
#include <mach-o/loader.h>
#include <mach-o/nlist.h>
#include <mach-o/ranlib.h>
#include <mach-o/reloc.h>
#include <mach-o/stab.h>
#include <mach-o/swap.h>
#include <mach-o/utils.h>
#include <mach/clock.h>
// Assembly helper macros such as addr16 collide with C field names.
// These three headers are individually compiled roots only.
#if defined(APPLE_C_PROBE_ASM_HEADERS)
#include <mach/arm/asm.h>
#include <mach/arm64/asm.h>
#endif
#include <mach/exception.h>
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/thread_state.h>
#include <mach/vm_param.h>
#include <malloc/malloc.h>
#include <memory.h>
#include <net/bpf.h>
#include <net/dlil.h>
#include <net/ethernet.h>
#include <net/if_arp.h>
#include <net/if_dl.h>
#include <net/if_llc.h>
#include <net/if_media.h>
#include <net/if_mib.h>
#include <net/if_types.h>
#include <net/if_utun.h>
#include <net/if_var.h>
#include <net/if_var_status.h>
#include <net/kext_net.h>
#include <net/ndrv.h>
#include <net/net_kev.h>
#include <net/pfkeyv2.h>
#include <net/route.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <nameser.h>
#include <notify.h>
#include <notify_keys.h>
#include <os/lock.h>
#if defined(APPLE_C_PROBE_PROVISIONAL_SOURCES)
#include <os/arch/arm64.h>
#endif
#include <os/proc.h>
#include <os/os_sync_wait_on_address.h>
#include <os/security_config.h>
#include <os/signpost.h>
#include <paths.h>
#include <pthread_impl.h>
#include <pthread_spis.h>
#include <removefile.h>
#include <resolv.h>
// Legacy rpcsvc interfaces are checked individually; they share generated
// identifiers with each other and with unrelated headers.
#if defined(APPLE_C_PROBE_LEGACY_RPCSVC)
#include <rpcsvc/bootparam_prot.h>
#include <rpcsvc/klm_prot.h>
#include <rpcsvc/mount.h>
#include <rpcsvc/nfs_prot.h>
#include <rpcsvc/nlm_prot.h>
#include <rpcsvc/rex.h>
#include <rpcsvc/rnusers.h>
#include <rpcsvc/rquota.h>
#include <rpcsvc/rstat.h>
#include <rpcsvc/rusers.h>
#include <rpcsvc/rwall.h>
#include <rpcsvc/sm_inter.h>
#include <rpcsvc/spray.h>
#include <rpcsvc/yp.h>
#include <rpcsvc/yppasswd.h>
#endif
#include <sandbox.h>
// Apple's servers/key_defs.h defines key_t differently from sys/types.h.
// Keep it as an individually compiled root; it cannot share this translation unit.
#if defined(APPLE_C_PROBE_LEGACY_SERVERS)
#include <servers/key_defs.h>
#endif
#include <servers/ls_defs.h>
#include <servers/netname.h>
#include <servers/netname_defs.h>
#include <servers/nm_defs.h>
#include <simd/simd.h>
#include <sys/acl.h>
#include <sys/attr.h>
#include <sys/clonefile.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/mount.h>
#include <sys/param.h>
#include <sys/paths.h>
#include <sys/random.h>
#include <sys/sysctl.h>
#include <sys/syscall.h>
#include <sys/timex.h>
#include <sysexits.h>
#include <timingsafe.h>
#include <ucontext.h>
#include <vis.h>
#include <xlocale.h>
#include <xpc/xpc.h>
#include <zlib.h>

int main(void) { return 0; }
