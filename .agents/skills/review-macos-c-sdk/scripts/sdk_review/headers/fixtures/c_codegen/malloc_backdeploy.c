#include <stdlib.h>
#include <malloc/malloc.h>

_Static_assert(__has_feature(typed_memory_operations) == REVIEW_TYPED,
               "unexpected typed-memory-operations mode");

#ifdef REVIEW_DIRECT
void review_direct(size_t size) {
  (void)malloc_type_malloc(size, 0);
}
#else
void *review_malloc(size_t size) {
  return malloc(size);
}

void *review_malloc_zone_malloc(malloc_zone_t *zone, size_t size) {
  return malloc_zone_malloc(zone, size);
}
#endif
