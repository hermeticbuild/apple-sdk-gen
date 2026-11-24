from __future__ import annotations

from dataclasses import dataclass, field

from .models.types import PlatformName


@dataclass
class PlatformConfig:
    name: PlatformName
    sdk_prefix: str
    platform_dir: str
    target_triples: list[str] = field(default_factory=list)


PLATFORM_CONFIGS: dict[str, PlatformConfig] = {
    "macos": PlatformConfig(
        name=PlatformName.MACOS,
        sdk_prefix="MacOSX",
        platform_dir="MacOSX.platform",
        target_triples=["arm64-apple-macos"],
    ),
}


def tbd_targets_for_platform(platform_key: str) -> list[str]:
    cfg = PLATFORM_CONFIGS[platform_key]
    return [f"{triple.split('-', 1)[0]}-{platform_key}" for triple in cfg.target_triples]


# Module names from the documentation API that are NOT real .framework
# bundles in any Apple SDK.  These are REST APIs, web JS libraries,
# documentation topics, Swift stdlib modules, or system dylibs.
NON_FRAMEWORK_MODULES: set[str] = {
    # ── REST APIs and web services ──
    "AdvancedCommerceAPI",
    "AppleMapsServerAPI",
    "AppleMusicAPI",
    "AppleMusicFeed",
    "AppleNews",
    "ApplePayMerchantTokenUsageInformation",
    "ApplePayontheWeb",
    "ApplePayWebMerchantRegistrationAPI",
    "AppLicenseDeliverySDK",
    "AppStoreConnectAPI",
    "AppStoreReceipts",
    "AppStoreServerAPI",
    "AppStoreServerNotifications",
    "AutomaticSignInAPI",
    "ClassKitCatalogAPI",
    "EnterpriseProgramAPI",
    "ExternalPurchaseServerAPI",
    "iWorkDocumentExportingAPI",
    "MerchantTokenNotificationServices",
    "NotaryAPI",
    "RetentionMessaging",
    "RosterAPI",
    "SigninwithApple",
    "SKAdNetworkforWebAds",
    "WeatherKitRESTAPI",
    # ── JavaScript / web libraries ──
    "CKToolJS",
    "CloudKitJS",
    "LivePhotosKitJS",
    "MapKitJS",
    "tvmljs",
    "webkitjs",
    # ── Documentation / meta topics ──
    "BundleResources",
    "SampleCode",
    "Snapshots",
    "TechnologyOverviews",
    "Updates",
    "SiriEventSuggestionsMarkup",
    # ── Miscellaneous non-SDK documentation ──
    "apple_ads",
    "professional_video_applications",
    "quicktime-file-format",
    # ── Swift stdlib modules (not .framework bundles) ──
    "Distributed",
    "ObjectiveC",
    "Observation",
    "PackageDescription",
    "RegexBuilder",
    "Swift",
    "Synchronization",
    "System",
    "Testing",
    # ── System libraries (dylibs, not .framework) ──
    "Compression",
    "DarwinNotify",
    "Dispatch",
    "dnssd",
    "os",
    "XPC",
    # ── Playground-specific ──
    "playgroundbluetooth",
    "playgroundsupport",
    # ── Low-level / kernel documentation ──
    "applicationservices",
    "kernel",
    # ── Other non-framework topics ──
    "AccessoryNotifications",
    "AccountDataTransfer",
    "AccountOrganizationalDataSharing",
    "AppDataTransfer",
    "ApplePencil",
    "SiriKitCloudMedia",
    "watchOS-Apps",
    "DeviceManagement",
}

# Framework name mappings: documentation API name → real .framework name.
# Applied at SDK assembly time so the generated bundle uses the correct name.
FRAMEWORK_NAME_MAPPINGS: dict[str, str] = {
    "PhotoKit": "Photos",
    "corefoundation": "CoreFoundation",
    "iokit": "IOKit",
    "coreservices": "CoreServices",
    "SiriKit": "Intents",
}

# Companion frameworks: when a main framework is assembled, also emit
# TBD-only stubs for its companions (no doc API entry of their own).
COMPANION_FRAMEWORKS: dict[str, list[str]] = {
    "Intents": ["IntentsUI"],
    "Photos": ["PhotosUI"],
    "IdentityLookup": ["IdentityLookupUI"],
    "SharedWithYou": ["SharedWithYouCore"],
}

# Frameworks with no doc API entry that need TBD-only stubs for linking.
SUPPLEMENTARY_FRAMEWORKS: list[str] = [
    "MobileCoreServices",   # Deprecated, re-exports CoreServices
    "OpenAL",               # Deprecated audio API
    "BusinessChat",         # Deprecated
    "Twitter",              # Deprecated
    "CoreMediaIO",          # Camera extensions (iOS 17+)
    "HealthKitUI",          # iOS 8+, in doc API but not in technologies listing
    "SecurityUI",           # No doc entry
    "StickerKit",           # No doc entry
]

# ── Shared exclusion categories ──

# Deprecated/legacy iOS-only frameworks
_DEPRECATED_MOBILE: set[str] = {
    "AssetsLibrary", "iAd", "Twitter",
}

# DriverKit sub-frameworks (macOS: System/DriverKit/ path, not System/Library/Frameworks/)
_DRIVERKIT_SUB: set[str] = {
    "AudioDriverKit", "BlockStorageDeviceDriverKit",
    "HIDDriverKit", "MIDIDriverKit", "NetworkingDriverKit",
    "PCIDriverKit", "SCSIControllerDriverKit",
    "SCSIPeripheralsDriverKit", "SerialDriverKit",
    "USBDriverKit", "USBSerialDriverKit",
}

# Developer tools (in Xcode Developer dir, not in SDK System/Library/Frameworks/)
_DEV_TOOLS: set[str] = {
    "Xcode", "XcodeKit", "XCTest", "XCUIAutomation",
}

# Documentation and companion frameworks omitted from the macOS SDK.
PLATFORM_EXCLUDED_MODULES: dict[str, set[str]] = {
    "macos": {
        # iOS/mobile-only
        "HealthKitUI", "IdentityLookupUI", "MarketplaceKit",
        "MessageUI", "MobileCoreServices", "UIKit", "hvf",
        # Not in macOS SDK System/Library/Frameworks
        "EndpointSecurity", "ShaderGraph", "Spatial",
        "StoreKitTest", "WalletOrders",
        # dylib, not a .framework
        "AppleArchive",
    } | _DEPRECATED_MOBILE | _DRIVERKIT_SUB | _DEV_TOOLS,

}


# Known framework re-export relationships
REEXPORTS: dict[str, list[str]] = {
    "Foundation": [
        "/usr/lib/libobjc.A.dylib",
        "/usr/lib/libSystem.B.dylib",
    ],
    "UIKit": [
        "/System/Library/Frameworks/Foundation.framework/Foundation",
        "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics",
    ],
    "AppKit": [
        "/System/Library/Frameworks/Foundation.framework/Foundation",
        "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics",
    ],
    "CoreFoundation": [
        "/usr/lib/libSystem.B.dylib",
    ],
}
