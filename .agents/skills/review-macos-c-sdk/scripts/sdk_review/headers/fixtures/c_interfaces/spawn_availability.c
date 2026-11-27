#include <spawn.h>

int add_working_directory(posix_spawn_file_actions_t *actions) {
  return posix_spawn_file_actions_addchdir(actions, ".");
}
