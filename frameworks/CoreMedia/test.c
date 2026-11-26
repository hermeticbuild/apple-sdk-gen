#include <CoreMedia/CMTimeRange.h>
#include <stddef.h>

_Static_assert(sizeof(CMTime) == 24, "CMTime ABI");
_Static_assert(offsetof(CMTime, epoch) == 16, "CMTime epoch offset");
_Static_assert(sizeof(CMTimeRange) == 48, "CMTimeRange ABI");

int main(void) {
    CMTime time = CMTimeMake(3, 30);
    CMTimeRange range = CMTimeRangeMake(kCMTimeZero, CMTimeMultiply(time, 2));
    return range.start.value != 0 || range.duration.value != 6 ||
        range.duration.timescale != 30 || range.duration.epoch != 0;
}
