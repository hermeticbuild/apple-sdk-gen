"""Exercise declaration, object and link capabilities of the official bundle."""

import json
from pathlib import Path

from tools.header_manifest import read_header_manifest


FIXTURES = Path(__file__).resolve().parent / "fixtures"
PARENT = "/usr/lib/libBootstrap.dylib"
CHILD = "/usr/lib/system/libBootstrapChild.dylib"
FUNCTIONS = {"_example_asm_name", "_example_function"}
TLS = "_example_tls"
BINDER = "dyld_stub_binder"
DIVIDE = "___udivti3"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def targets(library):
    return {row["target"] for row in library["target_info"]}


def symbols(library, target, segment, kind):
    return {
        symbol for group in library.get("exported_symbols", [])
        if "targets" not in group or target in group["targets"]
        for symbol in group.get(segment, {}).get(kind, [])
    }


def verify(llvm, work, c_install, lock, run, sha256):
    architectures = lock["target_architectures"]
    minimum = lock["minimum_deployment"]
    triples = {arch: f"{arch}-apple-macos{minimum}" for arch in architectures}
    expected_targets = {f"{arch}-macos" for arch in architectures}
    empty = work / "empty"
    empty.mkdir()
    resource = llvm / lock["resource_headers"]["path"]
    archive = llvm / lock["darwin_builtins"]["path"]
    paths = {work: "$WORK", llvm: "$LLVM", FIXTURES: "$FIXTURES"}
    if c_install is not None:
        c_install = c_install.resolve()
        paths[c_install] = "$C_INSTALL"
    commands = []

    def invoke(tool, *args):
        argv = [str(llvm / "bin" / tool), *(str(arg) for arg in args)]
        normalized = []
        for arg in argv:
            for path, label in paths.items():
                arg = arg.replace(str(path), label)
            normalized.append(arg)
        commands.append(normalized)
        return run(argv, cwd=work, env={"LC_ALL": "C"})

    def includes(sysroot):
        flags = ["-x", "c", "-std=c17", "-nostdinc", "-isysroot", sysroot, "-isystem", resource]
        if sysroot != empty:
            flags.extend(["-isystem", sysroot / "usr/include"])
        return flags

    def installapi(header, install_name, output, sysroot):
        inputs = work / f"{output.stem}.headers.json"
        inputs.write_text(json.dumps({
            "version": "3", "headers": [{"type": "public", "path": str(header)}],
        }))
        invoke("clang-installapi", *includes(sysroot),
               *(value for triple in triples.values() for value in ("-target", triple)),
               "-dynamiclib", "-install_name", install_name, "--filetype=tbd-v5",
               inputs, "-o", output)
        document = json.loads(output.read_text())
        library = document["main_library"]
        require(document["tapi_tbd_version"] == 5 and targets(library) == expected_targets,
                f"InstallAPI did not emit a two-target v5 document for {header}")
        require(library["install_names"] == [{"name": install_name}],
                f"InstallAPI emitted an unexpected install name for {header}")
        return library

    def compile_flags(arch, sysroot):
        return ["--no-default-config", "-target", triples[arch], *includes(sysroot)]

    def link(arch, output, *inputs, install_name):
        invoke("ld64.lld", "-dylib", "-install_name", install_name, "-arch", arch,
               "-platform_version", "macos", minimum, minimum, "-syslibroot", empty,
               "-o", output, *inputs)
        require(invoke("llvm-lipo", "-archs", output).split() == [arch],
                f"{output} has the wrong Mach-O slice")

    compiler = invoke("clang", "--version").splitlines()[0]
    linker = invoke("ld64.lld", "--version").strip()
    for version in (compiler, linker):
        require(lock["version"] in version and lock["commit"] in version,
                f"unexpected LLVM version: {version}")
    require(Path(invoke("clang", "-print-resource-dir").strip()).resolve() == resource.parent,
            "Clang selected a resource directory outside the pinned projection")
    builtins_arches = invoke("llvm-lipo", "-archs", archive).split()
    require(builtins_arches == lock["darwin_builtins"]["architectures"],
            f"unexpected builtins slices: {builtins_arches}")

    child = installapi(FIXTURES / "bootstrap.h", CHILD, work / "child.tbd", empty)
    umbrella = work / "libBootstrap.tbd"
    umbrella.write_text(json.dumps({
        "tapi_tbd_version": 5,
        "main_library": {
            "target_info": child["target_info"],
            "install_names": [{"name": PARENT}],
            "reexported_libraries": [{"names": [CHILD]}],
            "exported_symbols": [{"text": {"global": [BINDER]}}],
        },
        "libraries": [child],
    }, sort_keys=True) + "\n")

    capabilities = {}
    client = FIXTURES / "client.c"
    expected_imports = sorted(FUNCTIONS | {TLS})
    client_name = "/usr/lib/libClient.dylib"
    for arch in architectures:
        target = f"{arch}-macos"
        require(symbols(child, target, "text", "global") == FUNCTIONS and
                symbols(child, target, "data", "thread_local") == {TLS},
                f"{arch} InstallAPI exports did not preserve function, asm alias and TLS")
        extracted = work / f"{arch}.tbd"
        invoke("llvm-readtapi", "-extract", f"--arch={arch}", "--filetype=tbd-v5",
               umbrella, "-o", extracted)
        extracted_docs = json.loads(extracted.read_text())
        children = extracted_docs.get("libraries", [])
        require(extracted_docs["tapi_tbd_version"] == 5 and
                targets(extracted_docs["main_library"]) == {target} and len(children) == 1,
                f"{arch} llvm-readtapi extraction lost the embedded child")
        extracted_child = children[0]
        require(extracted_child["install_names"] == [{"name": CHILD}] and
                targets(extracted_child) == {target} and
                symbols(extracted_child, target, "text", "global") == FUNCTIONS and
                symbols(extracted_child, target, "data", "thread_local") == {TLS},
                f"{arch} llvm-readtapi extraction changed embedded child exports")
        ast = json.loads(invoke("clang", *compile_flags(arch, empty), "-fsyntax-only",
                                "-Xclang", "-ast-dump=json", client))
        declarations = {node.get("name"): node for node in ast["inner"]}
        require(declarations["example_function"]["mangledName"] == "_example_function" and
                declarations["example_aliased"]["mangledName"] == "_example_asm_name" and
                declarations["example_tls"]["tls"] == "static" and
                declarations["example_inline"]["inline"] and
                declarations["example_inline"]["storageClass"] == "static",
                f"{arch} AST did not preserve the four fixture declarations")

        obj = work / f"{arch}.o"
        output = work / f"{arch}.dylib"
        invoke("clang", *compile_flags(arch, empty), "-c", client, "-o", obj)
        imports = sorted(invoke("llvm-nm", "-uj", obj).split())
        require(imports == expected_imports, f"{arch} unexpected client object imports: {imports}")
        link(arch, output, obj, umbrella, install_name=client_name)
        dylibs = invoke("llvm-objdump", "--macho", "--dylibs-used", output)
        names = [line.split()[0] for line in dylibs.splitlines() if line.startswith("\t")]
        require(names == [client_name, PARENT], f"{arch} unexpected Mach-O load commands: {names}")
        bindings = invoke("llvm-objdump", "--macho", "--bind", "--lazy-bind", output)
        observed = {tuple(line.split()[-2:]) for line in bindings.splitlines()
                    if line.startswith("__")}
        require(observed == {("libBootstrap", name) for name in FUNCTIONS | {TLS, BINDER}},
                f"{arch} unexpected Mach-O bindings: {sorted(observed)}")
        capabilities[arch] = {
            "object_imports": imports,
            "bound_imports": {name: PARENT for _, name in sorted(observed)},
            "loaded_libraries": names[1:],
        }

    # Explicitly select the archive after observing a real header-free libcall.
    for arch in builtins_arches:
        obj = work / f"builtins-{arch}.o"
        output = work / f"builtins-{arch}.dylib"
        invoke("clang", *compile_flags(arch, empty), "-ffreestanding", "-c",
               FIXTURES / "builtins.c", "-o", obj)
        require(invoke("llvm-nm", "-uj", obj).split() == [DIVIDE],
                f"{arch} compiler did not emit the expected unsigned divide helper")
        link(arch, output, obj, archive, install_name="/usr/lib/libBuiltinProbe.dylib")
        require(DIVIDE in invoke("llvm-nm", "--defined-only", "-j", output).split() and
                not invoke("llvm-nm", "-uj", output).strip(),
                f"{arch} bundled builtins did not statically resolve {DIVIDE}")
        capabilities[arch]["static_builtin"] = DIVIDE

    result = {
        "clang": compiler,
        "linker": linker,
        "resource_directory": str(resource.parent.relative_to(llvm)),
        "targets": capabilities,
        "missing_builtin_slices": sorted(set(architectures) - set(builtins_arches)),
        "commands": commands,
        "generated_header": {"status": "skipped", "reason": "--c-install not supplied"},
    }
    if c_install is not None:
        relative = "usr/include/sys/stat.h"
        header = c_install / relative
        manifest, manifests = read_header_manifest(c_install)
        digest = sha256(header)
        require(manifest.get(relative, {}).get("sha256") == digest,
                f"generated header does not match its installation manifest: {header}")
        library = installapi(header, "/usr/lib/libGeneratedHeaderProbe.dylib",
                             work / "generated.tbd", c_install)
        actual = {}
        for arch in architectures:
            obj = work / f"stat-{arch}.o"
            invoke("clang", *compile_flags(arch, c_install), "-c", FIXTURES / "stat.c", "-o", obj)
            imports = invoke("llvm-nm", "-uj", obj).split()
            require(imports == ["_stat"] and "_stat" in symbols(library, f"{arch}-macos", "text", "global"),
                    f"{arch} generated stat header and object disagree: {imports}")
            actual[arch] = imports[0]
        source_lock = c_install / "source-lock.json"
        if source_lock.is_file():
            manifests.add(source_lock)
        result["generated_header"] = {
            "path": relative,
            "sha256": digest,
            "installation_inputs": {str(path.relative_to(c_install)): sha256(path)
                                    for path in sorted(manifests)},
            "symbols": actual,
        }
    return result
