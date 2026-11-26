#pragma once
#include <AudioToolbox/AudioToolbox.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef AudioComponentInstance AudioUnit;
extern OSStatus AudioUnitInitialize(AudioUnit unit);
extern OSStatus AudioUnitUninitialize(AudioUnit unit);

#ifdef __cplusplus
}
#endif
