# Check LLVM’s LCOV report

The upstream coverage script checks the report contents. Run it separately
from the Bazel integration suites on Apple Silicon.

From the SDK repository root, with the composed archive available:

```bash
(
  export USE_BAZEL_VERSION=9.3.2
  export PATH="/bin:$PATH"
  export LC_ALL=C
  cd e2e/llvm-stage1 || exit 1
  bazel query --bes_backend= 'set(@llvm//:MODULE.bazel @composed_sdk//sysroot:sysroot)' >/dev/null || exit 1
  output_base=$(bazel info output_base --bes_backend=) || exit 1
  sdk="$output_base/external/+http_archive+composed_sdk"
  cd "$output_base/external/llvm+/e2e/rules_cc" || exit 1
  /bin/bash ./coverage_lcov_test.sh \
    --platforms=@llvm//platforms:macos_arm64 \
    --remote_executor= --remote_cache= --experimental_remote_downloader= --bes_backend= \
    --lockfile_mode=off --symlink_prefix=/ --nocache_test_results --test_env=LC_ALL=C \
    --repo_env=BAZEL_MACOS_USE_HOST_SDK=0 \
    --extra_execution_platforms=@platforms//host \
    --@llvm//config:macos_libcxx_headers=sdk \
    "--override_repository=llvm++osx+macos_sdk=$sdk"
)
```
