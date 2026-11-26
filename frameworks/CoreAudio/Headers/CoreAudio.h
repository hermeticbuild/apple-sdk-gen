#pragma once
#include <CoreAudioTypes/CoreAudioTypes.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef UInt32 AudioObjectID;
typedef UInt32 AudioObjectPropertySelector;
typedef UInt32 AudioObjectPropertyScope;
typedef UInt32 AudioObjectPropertyElement;

typedef struct AudioObjectPropertyAddress {
    AudioObjectPropertySelector mSelector;
    AudioObjectPropertyScope mScope;
    AudioObjectPropertyElement mElement;
} AudioObjectPropertyAddress;

extern Boolean AudioObjectHasProperty(
    AudioObjectID object, const AudioObjectPropertyAddress *address);
extern OSStatus AudioObjectGetPropertyDataSize(
    AudioObjectID object, const AudioObjectPropertyAddress *address,
    UInt32 qualifierSize, const void *qualifier, UInt32 *size);

#ifdef __cplusplus
}
#endif
