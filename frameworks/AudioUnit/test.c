#include <AudioUnit/AudioUnit.h>

#include "../test-abi.h"

FUNCTION_TYPE(AudioUnitInitialize, OSStatus, AudioUnit);
FUNCTION_TYPE(AudioUnitUninitialize, OSStatus, AudioUnit);

int main(void) {
    return 0;
}
