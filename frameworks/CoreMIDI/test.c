#include <CoreMIDI/CoreMIDI.h>

#include "../test-abi.h"

FUNCTION_TYPE(MIDIGetNumberOfDevices, ItemCount, void);
FUNCTION_TYPE(MIDIGetDevice, MIDIDeviceRef, ItemCount);
_Static_assert(sizeof(MIDIDeviceRef) == 4, "MIDIDeviceRef");

int main(void) {
    return 0;
}
