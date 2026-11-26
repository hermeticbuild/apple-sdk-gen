#include <IOKit/audio/IOAudioTypes.h>

#include "../test-abi.h"

_Static_assert(kIOAudioEngineCurrentStatusStructVersion == 2, "IOAudioEngineStatus version");
_Static_assert(sizeof(IOAudioEngineStatus) == 20, "IOAudioEngineStatus");
FIELD_AT(IOAudioEngineStatus, fLastLoopTime, 8);
FIELD_AT(IOAudioEngineStatus, fEraseHeadSampleFrame, 16);

_Static_assert(sizeof(IOAudioStreamFormat) == 24, "IOAudioStreamFormat");
FIELD_AT(IOAudioStreamFormat, fBitDepth, 12);
FIELD_AT(IOAudioStreamFormat, fDriverTag, 20);

_Static_assert(sizeof(IOAudioTimeStamp) == 64, "IOAudioTimeStamp");
FIELD_AT(IOAudioTimeStamp, fSMPTETime, 32);
FIELD_AT(IOAudioTimeStamp, fFlags, 56);
