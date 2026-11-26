#pragma once
#include <MacTypes.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef UInt32 MIDIObjectRef;
typedef MIDIObjectRef MIDIDeviceRef;

extern ItemCount MIDIGetNumberOfDevices(void);
extern MIDIDeviceRef MIDIGetDevice(ItemCount index);

#ifdef __cplusplus
}
#endif
