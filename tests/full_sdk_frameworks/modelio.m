#import <ModelIO/ModelIO.h>

#ifdef __cplusplus
#define SAME_TYPE __is_same
#else
#define SAME_TYPE __builtin_types_compatible_p
#endif
_Static_assert(SAME_TYPE(__typeof__(((MDLMesh *)0).submeshes.firstObject), MDLSubmesh *),
               "MDLMesh submeshes preserve their element type through NSArray");

int main(void) {
    @autoreleasepool {
        return [MDLAsset class] == Nil;
    }
}
