#include <sys/stat.h>
int probe(const char *name, struct stat *out) { return stat(name, out); }
