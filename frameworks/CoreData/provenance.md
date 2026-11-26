# Core Data

Render the public Objective-C declarations for NSManagedObjectModel and
NSEntityDescription from Apple's documentation. Use the pinned Apple OSS
objc4 superclass through the Foundation package. The recipe runs InstallAPI
over the staged header to produce the two class exports. The Cocoa probe
sets an entity name and round-trips the entity through an in-memory model
using the real system Core Data library. Persistence and the other public
classes are outside the current profile.

- [NSManagedObjectModel](https://developer.apple.com/documentation/coredata/nsmanagedobjectmodel?language=objc)
- [NSEntityDescription](https://developer.apple.com/documentation/coredata/nsentitydescription?language=objc)
