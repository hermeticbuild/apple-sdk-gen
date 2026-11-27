#include <mach-o/dyld_images.h>

_Static_assert(sizeof(struct dyld_all_image_infos) == 368, "size");
_Static_assert(_Alignof(struct dyld_all_image_infos) == 16, "alignment");
_Static_assert(__builtin_offsetof(struct dyld_all_image_infos, notifyPorts) == 200, "port offset");
