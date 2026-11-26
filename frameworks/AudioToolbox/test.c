#include <AudioToolbox/AudioToolbox.h>

#include "../test-abi.h"

FUNCTION_TYPE(AudioComponentCount, UInt32, const AudioComponentDescription *);
FUNCTION_TYPE(AudioComponentFindNext, AudioComponent, AudioComponent,
              const AudioComponentDescription *);
FUNCTION_TYPE(AudioComponentGetDescription, OSStatus, AudioComponent,
              AudioComponentDescription *);
FUNCTION_TYPE(AudioComponentInstanceNew, OSStatus, AudioComponent, AudioComponentInstance *);
FUNCTION_TYPE(AudioComponentInstanceDispose, OSStatus, AudioComponentInstance);

_Static_assert(sizeof(AudioComponentDescription) == 20, "AudioComponentDescription");
FIELD_AT(AudioComponentDescription, componentType, 0);
FIELD_AT(AudioComponentDescription, componentSubType, 4);
FIELD_AT(AudioComponentDescription, componentManufacturer, 8);
FIELD_AT(AudioComponentDescription, componentFlags, 12);
FIELD_AT(AudioComponentDescription, componentFlagsMask, 16);

int main(void) {
    AudioComponentDescription wildcard = {0};
    return AudioComponentCount(&wildcard) == 0;
}
