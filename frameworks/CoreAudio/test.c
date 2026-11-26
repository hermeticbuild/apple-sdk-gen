#include <CoreAudio/AudioServerPlugIn.h>

#include "../test-abi.h"

FUNCTION_TYPE(AudioObjectHasProperty, Boolean, AudioObjectID,
              const AudioObjectPropertyAddress *);
FUNCTION_TYPE(AudioObjectGetPropertyDataSize, OSStatus, AudioObjectID,
              const AudioObjectPropertyAddress *, UInt32, const void *, UInt32 *);

_Static_assert(sizeof(AudioObjectPropertyAddress) == 12, "AudioObjectPropertyAddress");
FIELD_AT(AudioObjectPropertyAddress, mSelector, 0);
FIELD_AT(AudioObjectPropertyAddress, mScope, 4);
FIELD_AT(AudioObjectPropertyAddress, mElement, 8);

#define VTABLE_SLOT(field, slot) \
    FIELD_AT(AudioServerPlugInDriverInterface, field, (slot) * sizeof(void *))

_Static_assert(sizeof(AudioServerPlugInDriverInterface) == 23 * sizeof(void *),
               "AudioServerPlugInDriverInterface");
VTABLE_SLOT(_reserved, 0);
VTABLE_SLOT(QueryInterface, 1);
VTABLE_SLOT(AddRef, 2);
VTABLE_SLOT(Release, 3);
VTABLE_SLOT(Initialize, 4);
VTABLE_SLOT(CreateDevice, 5);
VTABLE_SLOT(DestroyDevice, 6);
VTABLE_SLOT(AddDeviceClient, 7);
VTABLE_SLOT(RemoveDeviceClient, 8);
VTABLE_SLOT(PerformDeviceConfigurationChange, 9);
VTABLE_SLOT(AbortDeviceConfigurationChange, 10);
VTABLE_SLOT(HasProperty, 11);
VTABLE_SLOT(IsPropertySettable, 12);
VTABLE_SLOT(GetPropertyDataSize, 13);
VTABLE_SLOT(GetPropertyData, 14);
VTABLE_SLOT(SetPropertyData, 15);
VTABLE_SLOT(StartIO, 16);
VTABLE_SLOT(StopIO, 17);
VTABLE_SLOT(GetZeroTimeStamp, 18);
VTABLE_SLOT(WillDoIOOperation, 19);
VTABLE_SLOT(BeginIOOperation, 20);
VTABLE_SLOT(DoIOOperation, 21);
VTABLE_SLOT(EndIOOperation, 22);

int main(void) {
    return 0;
}
