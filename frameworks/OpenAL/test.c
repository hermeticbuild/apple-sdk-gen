#include <OpenAL/al.h>
#include <OpenAL/alc.h>

#include "../test-abi.h"

FUNCTION_TYPE(alGetError, ALenum, void);
FUNCTION_TYPE(alcGetError, ALCenum, ALCdevice *);

int main(void) {
    return 0;
}
