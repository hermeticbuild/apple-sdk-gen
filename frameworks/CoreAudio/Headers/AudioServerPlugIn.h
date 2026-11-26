#pragma once
#include <CoreAudio/CoreAudio.h>
#include <CoreFoundation/CFDictionary.h>
#include <CoreFoundation/CFPlugInCOM.h>

typedef struct AudioServerPlugInHostInterface AudioServerPlugInHostInterface;
typedef const AudioServerPlugInHostInterface *AudioServerPlugInHostRef;
typedef struct AudioServerPlugInDriverInterface AudioServerPlugInDriverInterface;
typedef AudioServerPlugInDriverInterface **AudioServerPlugInDriverRef;

typedef struct AudioServerPlugInClientInfo AudioServerPlugInClientInfo;
typedef struct AudioServerPlugInIOCycleInfo AudioServerPlugInIOCycleInfo;

struct AudioServerPlugInDriverInterface {
    IUNKNOWN_C_GUTS;
    OSStatus (*Initialize)(AudioServerPlugInDriverRef, AudioServerPlugInHostRef);
    OSStatus (*CreateDevice)(AudioServerPlugInDriverRef, CFDictionaryRef,
                             const AudioServerPlugInClientInfo *, AudioObjectID *);
    OSStatus (*DestroyDevice)(AudioServerPlugInDriverRef, AudioObjectID);
    OSStatus (*AddDeviceClient)(AudioServerPlugInDriverRef, AudioObjectID,
                                const AudioServerPlugInClientInfo *);
    OSStatus (*RemoveDeviceClient)(AudioServerPlugInDriverRef, AudioObjectID,
                                   const AudioServerPlugInClientInfo *);
    OSStatus (*PerformDeviceConfigurationChange)(AudioServerPlugInDriverRef, AudioObjectID,
                                                 UInt64, void *);
    OSStatus (*AbortDeviceConfigurationChange)(AudioServerPlugInDriverRef, AudioObjectID,
                                               UInt64, void *);
    Boolean (*HasProperty)(AudioServerPlugInDriverRef, AudioObjectID, pid_t,
                           const AudioObjectPropertyAddress *);
    OSStatus (*IsPropertySettable)(AudioServerPlugInDriverRef, AudioObjectID, pid_t,
                                   const AudioObjectPropertyAddress *, Boolean *);
    OSStatus (*GetPropertyDataSize)(AudioServerPlugInDriverRef, AudioObjectID, pid_t,
                                    const AudioObjectPropertyAddress *,
                                    UInt32, const void *, UInt32 *);
    OSStatus (*GetPropertyData)(AudioServerPlugInDriverRef, AudioObjectID, pid_t,
                                const AudioObjectPropertyAddress *,
                                UInt32, const void *, UInt32, UInt32 *, void *);
    OSStatus (*SetPropertyData)(AudioServerPlugInDriverRef, AudioObjectID, pid_t,
                                const AudioObjectPropertyAddress *,
                                UInt32, const void *, UInt32, const void *);
    OSStatus (*StartIO)(AudioServerPlugInDriverRef, AudioObjectID, UInt32);
    OSStatus (*StopIO)(AudioServerPlugInDriverRef, AudioObjectID, UInt32);
    OSStatus (*GetZeroTimeStamp)(AudioServerPlugInDriverRef, AudioObjectID, UInt32,
                                 Float64 *, UInt64 *, UInt64 *);
    OSStatus (*WillDoIOOperation)(AudioServerPlugInDriverRef, AudioObjectID, UInt32,
                                   UInt32, Boolean *, Boolean *);
    OSStatus (*BeginIOOperation)(AudioServerPlugInDriverRef, AudioObjectID, UInt32,
                                  UInt32, UInt32, const AudioServerPlugInIOCycleInfo *);
    OSStatus (*DoIOOperation)(AudioServerPlugInDriverRef, AudioObjectID, AudioObjectID,
                               UInt32, UInt32, UInt32,
                               const AudioServerPlugInIOCycleInfo *, void *, void *);
    OSStatus (*EndIOOperation)(AudioServerPlugInDriverRef, AudioObjectID, UInt32,
                                UInt32, UInt32, const AudioServerPlugInIOCycleInfo *);
};
