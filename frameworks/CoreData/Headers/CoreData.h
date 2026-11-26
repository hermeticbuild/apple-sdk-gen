#pragma once

#import <Foundation/Foundation.h>

#ifdef __OBJC__
@interface NSEntityDescription : NSObject
@property (copy, nullable) NSString *name;
@end

@interface NSManagedObjectModel : NSObject
@property (strong) NSArray<NSEntityDescription *> *entities;
@end
#endif
