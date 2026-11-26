#pragma once
#include <MacTypes.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct OpaqueAudioComponent *AudioComponent;
typedef struct ComponentInstanceRecord *AudioComponentInstance;

typedef struct AudioComponentDescription {
    OSType componentType;
    OSType componentSubType;
    OSType componentManufacturer;
    UInt32 componentFlags;
    UInt32 componentFlagsMask;
} AudioComponentDescription;

extern UInt32 AudioComponentCount(const AudioComponentDescription *description);
extern AudioComponent AudioComponentFindNext(
    AudioComponent previous, const AudioComponentDescription *description);
extern OSStatus AudioComponentGetDescription(
    AudioComponent component, AudioComponentDescription *description);
extern OSStatus AudioComponentInstanceNew(
    AudioComponent component, AudioComponentInstance *instance);
extern OSStatus AudioComponentInstanceDispose(AudioComponentInstance instance);

#ifdef __cplusplus
}
#endif
