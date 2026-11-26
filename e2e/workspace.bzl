"""Make a fetched upstream test workspace available to the default runner."""

load("@rules_bazel_integration_test//bazel_integration_test:defs.bzl", "bazel_integration_test", "default_test_runner")

def _workspace_repository_impl(ctx):
    source = ctx.path(ctx.attr.module_file).dirname
    workspace = ctx.path("layout/source")

    # Keep the ancestors of the test workspace in this repository so the
    # child's relative module overrides and SDK path resolve together.
    for part in ctx.attr.subdirectory.split("/"):
        for entry in source.readdir():
            if entry.basename != part:
                ctx.symlink(entry, workspace.get_child(entry.basename))
        source = source.get_child(part)
        workspace = workspace.get_child(part)
    for entry in source.readdir():
        ctx.symlink(entry, workspace.get_child(entry.basename))

    ctx.symlink(ctx.path(ctx.attr.sdk_archive).dirname, "layout/sdk")
    if ctx.attr.llvm_module_file:
        ctx.symlink(ctx.path(ctx.attr.llvm_module_file).dirname, "layout/llvm")
    ctx.symlink(workspace, "workspace")
    ctx.file("BUILD.bazel", 'exports_files(["workspace"])\n')

workspace_repository = repository_rule(
    implementation = _workspace_repository_impl,
    attrs = {
        "llvm_module_file": attr.label(allow_single_file = True),
        "module_file": attr.label(allow_single_file = True, mandatory = True),
        "sdk_archive": attr.label(allow_single_file = True, mandatory = True),
        "subdirectory": attr.string(mandatory = True),
    },
)

def _workspace_runfiles_impl(ctx):
    return [DefaultInfo(runfiles = ctx.runfiles(symlinks = {"workspace": ctx.file.directory}))]

workspace_runfiles = rule(
    implementation = _workspace_runfiles_impl,
    attrs = {"directory": attr.label(allow_single_file = True, mandatory = True)},
)

def consumer_test(name, bazel_binaries, bazel_version, workspace, sdk_path, args, manual = False):
    """Run a single Bazel command in an upstream root workspace."""
    runner = name + "_runner"
    default_test_runner(
        name = runner,
        # A single command ensures the upstream runner returns its status.
        bazel_cmds = [" ".join([
            "--nohome_rc",
            "test",
            "--remote_executor=",
            "--remote_cache=",
            "--experimental_remote_downloader=",
            "--bes_backend=",
            "--lockfile_mode=off",
            "--symlink_prefix=/",
            "--nocache_test_results",
            # Bazel's XML reporter sets LC_ALL=C itself. Start in that locale
            # to avoid a crash in Homebrew Bash when it restores the locale.
            "--test_env=LC_ALL=C",
            "--local_test_jobs=2",
            "--repo_env=BAZEL_MACOS_USE_HOST_SDK=0",
            "--extra_execution_platforms=@platforms//host",
            "--@llvm//config:macos_libcxx_headers=sdk",
            "--override_repository=llvm++osx+macos_sdk=" + sdk_path,
        ] + args)],
    )
    bazel_integration_test(
        name = name,
        bazel_binaries = bazel_binaries,
        bazel_version = bazel_version,
        data = [workspace, "@composed_sdk//:MacOSX.sdk.tar.zst"],
        additional_env_inherit = ["PATH"],
        env = {"LC_ALL": "C"},
        tags = ["exclusive", "external", "local", "requires-network"] + (["manual"] if manual else []),
        test_runner = ":" + runner,
        timeout = "eternal",
    )
