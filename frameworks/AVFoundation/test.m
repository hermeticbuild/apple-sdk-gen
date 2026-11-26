#import <AVFoundation/AVCaptureSession.h>
#import <AVFoundation/AVAssetWriterInput.h>

int main(void) {
    @autoreleasepool {
        AVCaptureSession *session = [AVCaptureSession new];
        session.sessionPreset = AVCaptureSessionPresetMedium;
        AVAssetWriterInput *input = [AVAssetWriterInput assetWriterInputWithMediaType:AVMediaTypeVideo
                                                                      outputSettings:nil];
        return input == nil || ![session.sessionPreset isEqualToString:AVCaptureSessionPresetMedium];
    }
}
