"""Compose an SDK from verified C headers and explicitly selected SDK assets.

The output records selected files, symlinks and install-name providers in composition.json.
External aliases require their targets to be selected at the corresponding SDK paths.
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from tools.header_manifest import read_header_manifest
from tools.tbd import read_install_names, read_json
from tools.fetch_sources import ROOT as REPO_ROOT, read_lock


STUB = Path("usr/lib/libSystem.B.tbd")
ALIAS = Path("usr/lib/libSystem.tbd")
SYSTEM_INSTALL_NAME = "/usr/lib/libSystem.B.dylib"
# Apple's macOS Libsystem-1356 install script gives these names to the
# umbrella. SDK Gen emits some of them as standalone reexport stubs.
# https://github.com/apple-oss-distributions/Libsystem/blob/c23b51183e46e613375dc7639fb4bf11fbf59ba8/xcodescripts/create_dylib_symlinks.sh#L14-L31
SYSTEM_COMPAT_NAMES = ("c", "dbm", "dl", "gcc_s.1", "info", "m", "poll", "proc", "pthread", "rpcsvc")
FRAMEWORKS = Path("System/Library/Frameworks")
CXX_HEADERS = Path("usr/include/c++/v1")
CXX_LICENSES = tuple(Path("usr/share/licenses") / name / "LICENSE.TXT"
                     for name in ("libcxx", "libcxxabi"))
SDK_VERSION = "26.5"
SDK_NAME = "macosx" + SDK_VERSION
CONSUMER_PROFILE = Path(__file__).with_name("consumer-26.5.json")
MACHO_MAGIC = {
    b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",
}


def digest(path):
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def relative_path(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or path.as_posix() != value:
        raise ValueError(f"expected a canonical SDK-relative path: {value!r}")
    return path


def allowed_path(path, layer):
    cxx_path = path == CXX_HEADERS.parent or path.is_relative_to(CXX_HEADERS)
    if ((path.is_relative_to(CXX_HEADERS.parent) and (not cxx_path or layer != "sdk-gen-cxx"))
            or path.suffix in {".a", ".dylib"}):
        raise ValueError(f"toolchain or binary asset cannot enter the composed SDK: {path}")


@dataclass(frozen=True)
class File:
    source: Path
    source_root: Path
    layer: str
    sha256: str | None
    symlink: str | None


class Plan:
    def __init__(self):
        self.files = {}
        self.directories = set()
        self.replaced = {}
        self.generated_paths = defaultdict(set)

    def directory(self, path, layer):
        allowed_path(path, layer)
        for destination in (path, *path.parents):
            if destination in self.files:
                raise ValueError(f"SDK path collision: {destination}")
            self.directories.add(destination)

    def file(self, destination, source, source_root, layer, sha256=None, *, symlink=None):
        allowed_path(destination, layer)
        self.directory(destination.parent, layer)
        original = destination
        if layer == "framework-overlay" and original not in self.files:
            # DocC can capitalize a C header differently from its source.
            # Keep the spelling supplied by the replacement recipe.
            matches = self.generated_paths.get((destination.parent, destination.name.casefold()), ())
            if len(matches) > 1:
                raise ValueError(f"ambiguous SDK Gen file spelling: {destination}")
            if matches:
                original = next(iter(matches))
                if original not in self.files:
                    raise ValueError(f"SDK path collision: {destination}")
        previous = self.files.get(original)
        replaces_generated_file = (
            previous is not None and layer == "framework-overlay" and previous.layer == "sdk-gen-framework"
        )
        if destination in self.directories or (previous is not None and not replaces_generated_file):
            raise ValueError(f"SDK path collision: {destination}")
        mode = source.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
            raise ValueError(f"unsupported SDK file type: {source}")
        link = os.readlink(source) if stat.S_ISLNK(mode) else None
        if symlink is not None and link != symlink:
            raise ValueError(f"{destination} must be a relative alias to {symlink}")
        if link is not None and Path(link).is_absolute():
            raise ValueError(f"absolute symlink in SDK source: {source}")
        try:
            resolved = source.resolve(strict=True)
        except (OSError, RuntimeError) as err:
            raise ValueError(f"invalid SDK input path or symlink {source}: {err}") from err
        if not resolved.is_relative_to(source_root):
            raise ValueError(f"SDK source symlink escapes selected input: {source}")
        if replaces_generated_file:
            del self.files[original]
            self.replaced[destination] = previous
        elif layer == "sdk-gen-framework":
            self.generated_paths[destination.parent, destination.name.casefold()].add(destination)
        self.files[destination] = File(source, source_root, layer, sha256, link)

    def tree(self, destination, source, source_root, layer):
        self.directory(destination, layer)
        for path in sorted(source.iterdir()):
            out = destination / path.name
            if path.is_dir() and not path.is_symlink():
                self.tree(out, path, source_root, layer)
            else:
                self.file(out, path, source_root, layer)

    def materialize(self, root):
        receipts = {}
        for path in sorted(self.directories):
            dest = root / path
            dest.mkdir(parents=True, exist_ok=True)
            dest.chmod(0o755)

        for path, file in sorted(self.files.items()):
            dest = root / path
            receipt = {"layer": file.layer, "source": file.source.relative_to(file.source_root).as_posix()}
            if file.symlink is not None:
                dest.symlink_to(file.symlink)
                receipt["symlink"] = file.symlink
            else:
                with file.source.open("rb") as stream, dest.open("xb") as output:
                    prefix = stream.read(8)
                    if prefix[:4] in MACHO_MAGIC or prefix in {b"!<arch>\n", b"!<thin>\n"}:
                        raise ValueError(f"binary or archive in SDK input: {path}")
                    output.write(prefix)
                    shutil.copyfileobj(stream, output)
                dest.chmod(0o644)
                receipt["sha256"] = digest(dest)
            receipts[path.as_posix()] = receipt

        for path, file in sorted(self.files.items()):
            dest = root / path
            if dest.is_symlink():
                try:
                    resolved = dest.resolve(strict=True)
                except (OSError, RuntimeError) as err:
                    raise ValueError(f"SDK symlink has no selected target: {path}") from err
                if not resolved.is_relative_to(root):
                    raise ValueError(f"SDK symlink escapes composed SDK: {path}")
                target = resolved.relative_to(root)
                source_target = file.source.resolve(strict=True)
                if resolved.is_dir():
                    # Framework version aliases must keep pointing within the
                    # selected framework. Header installs list individual files.
                    if file.layer not in {"sdk-gen-framework", "prepared-framework", "framework-overlay"} or not target.is_relative_to(
                            FRAMEWORKS / path.parts[len(FRAMEWORKS.parts)]):
                        raise ValueError(f"SDK directory alias escapes its selected framework: {path}")
                else:
                    selected = self.files.get(target)
                    # A generated alias still points at the same SDK path when
                    # an explicit overlay replaces its original regular file.
                    if file.layer == "sdk-gen-framework":
                        selected = self.replaced.get(target, selected)
                    if (selected is None or selected.layer != file.layer or
                            selected.source.resolve() != source_target):
                        raise ValueError(f"SDK symlink target differs from selected source: {path}")
                if path.suffix == ".tbd" and (not resolved.is_file() or target.suffix != ".tbd"):
                    raise ValueError(f"TBD alias does not resolve to a selected TBD: {path}")
            if file.sha256 is not None:
                if not dest.is_file() or digest(dest) != file.sha256:
                    raise ValueError(f"SDK file differs from its input manifest: {path}")
        return receipts


def c_install(plan, root):
    files, metadata = read_header_manifest(root)
    for name, receipt in sorted(files.items()):
        path = relative_path(name)
        if not path.is_relative_to("usr/include") or path == Path("usr/include"):
            raise ValueError(f"C header manifest path outside usr/include: {path}")
        plan.file(path, root / path, root, "c-install", receipt["sha256"])
    for source in sorted(metadata):
        if source.is_symlink():
            raise ValueError(f"C installation manifest is a symlink: {source}")
        plan.file(source.relative_to(root), source, root, "c-install", digest(source))


def objc4_headers(plan, root):
    files, _ = read_header_manifest(root)
    include = Path("usr/include/objc")
    for name, record in sorted(files.items()):
        path = relative_path(name)
        if (path.parent != include or path.suffix != ".h" or record["owner"] != "objc4"
                or record["origin"] != f"sources/objc4/runtime/{path.name}"):
            raise ValueError(f"unexpected objc4 header receipt: {path}")
        source = root / path
        if source.is_symlink() or not source.is_file() or source.resolve() != source:
            raise ValueError(f"objc4 public header must be a regular staged file: {source}")
        plan.file(path, source, root, "objc4-public-headers", record["sha256"])


def sdk_gen_cxx_headers(plan, root):
    headers = root / CXX_HEADERS
    for name in ("__config_site", "module.modulemap", "cxxabi.h", "__cxxabi_config.h"):
        if not (headers / name).is_file():
            raise ValueError(f"SDK Gen C++ installation is missing {CXX_HEADERS / name}")
    plan.tree(CXX_HEADERS, headers, root, "sdk-gen-cxx")
    for path in CXX_LICENSES:
        plan.file(path, root / path, root, "sdk-gen-cxx")


def sdk_gen_simd_headers(plan, root):
    include = Path("usr/include/simd")
    if not (root / include).exists():
        return
    for name in ("simd.h", "module.modulemap"):
        path = include / name
        source = root / path
        if not source.is_file():
            raise ValueError(f"SDK Gen SIMD installation is missing {path}")
        plan.file(path, source, root, "sdk-gen-simd")


def sdk_settings(sdk, receipts):
    settings = {"CanonicalName": SDK_NAME, "Version": SDK_VERSION, "MaximumDeploymentTarget": SDK_VERSION,
                "SupportedTargets": {"macosx": {"Archs": ["arm64"], "LLVMTargetTripleVendor": "apple",
                                                 "LLVMTargetTripleSys": "macosx"}}}
    path = sdk / "SDKSettings.json"
    path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n")
    receipts[path.name] = {"layer": "sdk-settings", "source": f"c-install:{SDK_NAME}", "sha256": digest(path)}


def framework(plan, sdk_gen, name, *, prepared=None, overlay=None):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*", name):
        raise ValueError(f"invalid SDK Gen framework name: {name}")
    relative = FRAMEWORKS / f"{name}.framework"
    source = overlay or prepared or sdk_gen / relative
    if (source.name != relative.name or source.is_symlink() or not source.is_dir()
            or (prepared is None and overlay is None and not source.resolve().is_relative_to(sdk_gen))):
        raise ValueError(f"missing or escaped framework: {relative}")
    source = source.resolve()
    layer = "framework-overlay" if overlay else "prepared-framework" if prepared else "sdk-gen-framework"
    plan.tree(relative, source, source, layer)


def frameworks(plan, sdk_gen, args):
    names = set(args.framework)
    prepared = dict(args.prepared_framework)
    overlays = dict(args.framework_overlay)
    if len(prepared) != len(args.prepared_framework) or len(overlays) != len(args.framework_overlay):
        raise ValueError("multiple prepared bundles or overlays for a framework")
    if names & prepared.keys():
        raise ValueError("a framework cannot be selected and supplied as a prepared bundle")
    if args.all_frameworks:
        root = sdk_gen / FRAMEWORKS
        if not root.is_dir():
            raise ValueError(f"missing SDK Gen framework directory: {root}")
        names.update(path.stem for path in root.glob("*.framework") if path.is_dir())
        names.difference_update(prepared)
    if overlays.keys() - names:
        raise ValueError("framework overlays require a selected SDK Gen base bundle: " +
                         ", ".join(sorted(overlays.keys() - names)))
    for name in sorted(names):
        framework(plan, sdk_gen, name)
    for name, source in sorted(prepared.items()):
        framework(plan, sdk_gen, name, prepared=Path(source))
    for name, source in sorted(overlays.items()):
        framework(plan, sdk_gen, name, overlay=Path(source))


def external_stub(plan, spec):
    destination, separator, source = spec.partition("=")
    if not separator or not source:
        raise ValueError("--external-stub requires SDK/relative/path.tbd=/source/path.tbd")
    path = relative_path(destination)
    source = Path(source).absolute()
    if not path.is_relative_to("usr/lib") or path.suffix != ".tbd":
        raise ValueError(f"external stub destination must be a .tbd under usr/lib: {path}")
    if source.suffix != ".tbd" or not source.is_file():
        raise ValueError(f"external stub source must resolve to a regular .tbd file: {source}")
    source_root = source.parent.resolve()
    plan.file(path, source_root / source.name, source_root, "external-stub")


def sdk_gen_libsystem(plan, root):
    links = root / STUB.parent
    if (root / STUB).is_symlink() or not (root / STUB).is_file():
        raise ValueError("SDK Gen must supply a regular libSystem.B.tbd")
    plan.file(STUB, root / STUB, root, "sdk-gen-libsystem")
    plan.file(ALIAS, root / ALIAS, root, "sdk-gen-libsystem", symlink=STUB.name)
    for path in sorted(links.glob("*.tbd")):
        if path != root / ALIAS and path.is_symlink() and path.resolve() == root / STUB:
            plan.file(path.relative_to(root), path, root, "sdk-gen-libsystem")
    for name in SYSTEM_COMPAT_NAMES:
        path = STUB.parent / f"lib{name}.tbd"
        if path not in plan.files:
            plan.file(path, root / ALIAS, root, "sdk-gen-libsystem")


def providers(plan, root, llvm):
    reader = llvm / "bin/llvm-readtapi"
    umbrella = (root / STUB).read_text(encoding="utf-8")
    system_names = read_install_names(umbrella, reader)
    if not system_names or system_names[0] != SYSTEM_INSTALL_NAME:
        raise ValueError("SDK Gen libSystem umbrella has the wrong install name")
    locations = defaultdict(list, {name: [STUB.as_posix()] for name in system_names})
    for path in sorted(plan.files):
        source = root / path
        if path == STUB or source.is_symlink():
            continue
        content = source.read_bytes()
        start = content.lstrip()
        if (path.suffix != ".tbd" and not start.startswith(b"--- !tapi-tbd") and
                not (start.startswith(b"{") and b'"tapi_tbd_version"' in content)):
            continue
        try:
            names = read_install_names(content.decode("utf-8"), reader)
        except (ValueError, OSError) as err:
            raise ValueError(f"cannot account for TBD providers in {path}: {err}") from err
        for name in names:
            if name in system_names:
                raise ValueError(f"{path} shadows SDK Gen libSystem install name {name} in {STUB}")
            locations[name].append(path.as_posix())
    return locations


def consumer_assets(files):
    groups = defaultdict(list)
    for path, receipt in sorted(files.items()):
        layer = receipt["layer"]
        if layer in ("sdk-gen-framework", "prepared-framework", "framework-overlay"):
            group = Path(path).parts[len(FRAMEWORKS.parts)]
        elif layer in ("sdk-gen-libsystem", "sdk-gen-cxx", "sdk-gen-simd", "external-stub"):
            group = layer
        else:
            continue
        kind = "symlink" if "symlink" in receipt else "sha256"
        groups[group].append([path, layer, kind, receipt[kind]])
    return {
        group: hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
        for group, rows in groups.items()
    }


def verify_consumer_inputs(composition, profile):
    if not composition.get("objc4_revision"):
        raise ValueError("consumer profile requires the pinned SDK Gen version and objc4 layer")
    actual = consumer_assets(composition["files"])
    expected = profile["asset_sha256"]
    mismatches = sorted(name for name in actual.keys() | expected.keys()
                        if actual.get(name) != expected.get(name))
    if mismatches:
        raise ValueError("consumer assets differ from the qualified profile: " + ", ".join(mismatches))


def check_sdk_gen_version(root, expected, option):
    settings = read_json((root / "SDKSettings.json").read_bytes())
    if not isinstance(settings, dict):
        raise ValueError(f"{option} has invalid SDKSettings.json at {root}")
    name, version = settings.get("CanonicalName"), settings.get("Version")
    if name != expected or version != expected.removeprefix("macosx"):
        raise ValueError(
            f"{option} requires {expected}, got CanonicalName={name!r} and Version={version!r} at {root}"
        )


def compose(args):
    out = args.out.parent.resolve() / args.out.name
    if os.path.lexists(out):
        raise ValueError(f"output already exists: {out}")
    c_root = args.c_install.resolve()
    objc_root = args.objc4_install.resolve() if args.objc4_install else None
    sdk_gen = args.sdk_gen.resolve()
    framework_sdk = args.framework_sdk_gen.resolve() if args.framework_sdk_gen else sdk_gen
    # Replay the older consumer archive only with its existing exact-asset check.
    profile = read_json(CONSUMER_PROFILE.read_bytes()) if args.verify_consumer_inputs else None
    expected_sdk_gen = profile["sdk_gen"] if profile else SDK_NAME
    check_sdk_gen_version(sdk_gen, expected_sdk_gen, "--sdk-gen")
    if framework_sdk != sdk_gen:
        check_sdk_gen_version(framework_sdk, expected_sdk_gen, "--framework-sdk-gen")
    expected_lock, _ = read_lock(REPO_ROOT / "locks" / f"{SDK_NAME}.json")
    lock = c_root / "source-lock.json"
    if lock.is_symlink() or lock.read_bytes() != expected_lock:
        raise ValueError(f"composition requires the pinned {SDK_NAME} C installation")
    objc4_revision = None
    if objc_root:
        expected_lock, projects = read_lock(REPO_ROOT / "locks" / f"{SDK_NAME}-objc4.json")
        lock = objc_root / "source-lock.json"
        if lock.is_symlink() or lock.read_bytes() != expected_lock:
            raise ValueError(f"objc4 installation does not match the {SDK_NAME} source lock")
        objc4_revision = projects["objc4"]["commit"]

    plan = Plan()
    c_install(plan, c_root)
    sdk_gen_libsystem(plan, sdk_gen)
    if objc_root:
        objc4_headers(plan, objc_root)
    if args.include_cxx:
        sdk_gen_cxx_headers(plan, sdk_gen)
    sdk_gen_simd_headers(plan, framework_sdk)
    frameworks(plan, framework_sdk, args)
    for spec in args.external_stub:
        external_stub(plan, spec)

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".compose-sdk-", dir=out.parent) as temporary:
        sdk = Path(temporary) / "SDK"
        sdk.mkdir()
        receipts = plan.materialize(sdk)
        sdk_settings(sdk, receipts)
        composition = {
            "schema": 1,
            "files": receipts,
            "sdk_gen": expected_sdk_gen,
            "providers": providers(plan, sdk, args.llvm.resolve()),
        }
        if objc4_revision:
            composition["objc4_revision"] = objc4_revision
        if args.framework_sdk_gen:
            composition["framework_sdk_gen"] = expected_sdk_gen
        if profile:
            verify_consumer_inputs(composition, profile)
        manifest = sdk / "composition.json"
        manifest.write_text(json.dumps(composition, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest.chmod(0o644)
        if os.path.lexists(out):
            raise ValueError(f"output already exists: {out}")
        sdk.rename(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("c-install", "llvm", "out", "sdk-gen"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--objc4-install", type=Path,
                        help="separate Objective-C runtime headers from make install-objc4")
    parser.add_argument("--include-cxx", action="store_true",
                        help="include the LLVM C++ and ABI headers supplied by --sdk-gen")
    parser.add_argument("--verify-consumer-inputs", action="store_true",
                        help="require the assets from the qualified macOS 26.5 consumer archive")
    parser.add_argument("--framework", action="append", default=[], help="public SDK Gen framework name")
    parser.add_argument("--all-frameworks", action="store_true",
                        help="select every SDK Gen System/Library/Frameworks bundle")
    parser.add_argument("--framework-sdk-gen", type=Path,
                        help="SDK Gen framework input, separately from the libSystem input")
    parser.add_argument("--prepared-framework", nargs=2, action="append", default=[], metavar=("NAME", "DIRECTORY"),
                        help="supply an entire prepared framework bundle")
    parser.add_argument("--framework-overlay", nargs=2, action="append", default=[], metavar=("NAME", "DIRECTORY"),
                        help="add or replace explicit files in a selected SDK Gen framework")
    parser.add_argument("--external-stub", action="append", default=[], metavar="DESTINATION=SOURCE",
                        help="select one .tbd or relative alias at a path below usr/lib")
    args = parser.parse_args()
    try:
        compose(args)
    except (OSError, ValueError, KeyError) as err:
        parser.exit(1, f"compose-sdk: {err}\n")


if __name__ == "__main__":
    main()
