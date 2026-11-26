#pragma once

#ifdef __OBJC__
#import <Foundation/Foundation.h>

@interface CALayer : NSObject
+ (instancetype)layer;
@property (strong) id contents;
@end
#endif
