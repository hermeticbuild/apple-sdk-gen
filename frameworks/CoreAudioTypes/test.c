#include <CoreAudioTypes/CoreAudioTypes.h>

#include "../test-abi.h"

_Static_assert(sizeof(AudioStreamBasicDescription) == 40, "AudioStreamBasicDescription");
FIELD_AT(AudioStreamBasicDescription, mSampleRate, 0);
FIELD_AT(AudioStreamBasicDescription, mFormatID, 8);
FIELD_AT(AudioStreamBasicDescription, mFormatFlags, 12);
FIELD_AT(AudioStreamBasicDescription, mBytesPerPacket, 16);
FIELD_AT(AudioStreamBasicDescription, mFramesPerPacket, 20);
FIELD_AT(AudioStreamBasicDescription, mBytesPerFrame, 24);
FIELD_AT(AudioStreamBasicDescription, mChannelsPerFrame, 28);
FIELD_AT(AudioStreamBasicDescription, mBitsPerChannel, 32);
FIELD_AT(AudioStreamBasicDescription, mReserved, 36);
