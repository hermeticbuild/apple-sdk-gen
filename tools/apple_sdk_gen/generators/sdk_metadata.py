from __future__ import annotations

import json
import plistlib

from ..config import PLATFORM_CONFIGS

DEFAULT_COMPILER = "com.apple.compilers.llvm.clang.1_0"

_MAC = {"Name": "mac", "DisplayName": "Mac"}
PLATFORMS = {
    "macos": {
        "env": "",
        "name": "macosx",
        "family": "macosx",
        "family_name": "macOS",
        "display": "macOS",
        "product": "macOS",
        "sys": "macos",
        "runtime": "osx",
        "build_id": "1",
        "minimum": "12.0",
        "families": [_MAC],
    },
}


def default_xcode_version(sdk_version: str) -> str:
    major, _, minor = sdk_version.partition(".")
    if int(major) >= 26:
        return sdk_version
    return "{}.{}".format(int(major) - 10, minor or "0")


def default_xcode_build(xcode_version: str) -> str:
    return xcode_version.split(".")[0] + "A0"


def _archs(platform_key: str) -> list[str]:
    return [triple.split("-")[0] for triple in PLATFORM_CONFIGS[platform_key].target_triples]


def _default_properties(platform_key: str) -> dict[str, str]:
    platform = PLATFORMS[platform_key]
    return {
        "CODE_SIGN_IDENTITY": "-",
        "DEAD_CODE_STRIPPING": "YES",
        "DEFAULT_COMPILER": DEFAULT_COMPILER,
        "ENTITLEMENTS_REQUIRED": "NO",
        "PLATFORM_NAME": platform["name"],
    }


def sdk_settings(platform_key: str, sdk_version: str) -> dict:
    platform = PLATFORMS[platform_key]
    target = {
        "Archs": _archs(platform_key),
        "BuildVersionPlatformID": platform["build_id"],
        "ClangRuntimeLibraryPlatformName": platform["runtime"],
        "DefaultDeploymentTarget": sdk_version,
        "DeviceFamilies": platform["families"],
        "LLVMTargetTripleEnvironment": platform["env"],
        "LLVMTargetTripleSys": platform["sys"],
        "LLVMTargetTripleVendor": "apple",
        "MaximumDeploymentTarget": sdk_version + ".99",
        "MinimumDeploymentTarget": platform["minimum"],
        "PlatformFamilyName": platform["family_name"],
        "SystemPrefix": "",
    }
    return {
        "CanonicalName": platform["name"] + sdk_version,
        "CustomProperties": {},
        "DefaultDeploymentTarget": sdk_version,
        "DefaultProperties": _default_properties(platform_key),
        "DisplayName": "{} {}".format(platform["display"], sdk_version),
        "IsBaseSDK": "YES",
        "MaximumDeploymentTarget": sdk_version + ".99",
        "MinimalDisplayName": sdk_version,
        "SupportedTargets": {platform["name"]: target},
        "Version": sdk_version,
    }


def generate_sdk_settings(platform_key: str, sdk_version: str) -> str:
    return json.dumps(sdk_settings(platform_key, sdk_version), indent=2, sort_keys=True) + "\n"


def generate_sdk_settings_plist(platform_key: str, sdk_version: str) -> bytes:
    return plistlib.dumps(sdk_settings(platform_key, sdk_version), sort_keys=True)


def generate_info_plist(platform_key: str, sdk_version: str) -> bytes:
    platform = PLATFORMS[platform_key]
    sdk_prefix = PLATFORM_CONFIGS[platform_key].sdk_prefix
    return plistlib.dumps({
        "AdditionalInfo": {
            "CFBundleSupportedPlatforms": [sdk_prefix],
            "DTPlatformName": platform["name"],
            "DTPlatformVersion": sdk_version,
        },
        "CFBundleIdentifier": "com.apple.platform." + platform["name"],
        "CFBundleName": sdk_prefix,
        "CFBundleShortVersionString": sdk_version,
        "CFBundleVersion": sdk_version,
        "DefaultProperties": {
            "DEFAULT_COMPILER": DEFAULT_COMPILER,
            "PLATFORM_NAME": platform["name"],
        },
        "Description": platform["family_name"],
        "FamilyIdentifier": platform["family"],
        "FamilyName": platform["family_name"],
        "Identifier": "com.apple.platform." + platform["name"],
        "Name": platform["name"],
        "Type": "Platform",
        "Version": sdk_version,
    }, sort_keys=True)


def generate_system_version_plist(platform_key: str, sdk_version: str, build: str) -> bytes:
    return plistlib.dumps({
        "ProductBuildVersion": build,
        "ProductName": PLATFORMS[platform_key]["product"],
        "ProductVersion": sdk_version,
    }, sort_keys=True)


def generate_xcode_version_plist(xcode_version: str, xcode_build: str) -> bytes:
    return plistlib.dumps({
        "CFBundleShortVersionString": xcode_version,
        "CFBundleVersion": xcode_version,
        "ProductBuildVersion": xcode_build,
    }, sort_keys=True)
