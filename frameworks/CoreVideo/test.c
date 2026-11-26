#include <CoreVideo/CVPixelBuffer.h>

int main(void) {
    CVPixelBufferRef pixel = NULL;
    if (CVPixelBufferCreate(NULL, 16, 8, kCVPixelFormatType_32BGRA, NULL, &pixel) != kCVReturnSuccess)
        return 1;
    CVReturn locked = CVPixelBufferLockBaseAddress(pixel, 0);
    int result = locked != kCVReturnSuccess || CVPixelBufferGetBaseAddress(pixel) == NULL ||
        CVPixelBufferGetWidth(pixel) != 16 || CVPixelBufferGetHeight(pixel) != 8 ||
        CVPixelBufferGetBytesPerRow(pixel) < 64 || CVPixelBufferIsPlanar(pixel);
    if (locked == kCVReturnSuccess)
        CVPixelBufferUnlockBaseAddress(pixel, 0);
    CVPixelBufferRelease(pixel);
    return result;
}
