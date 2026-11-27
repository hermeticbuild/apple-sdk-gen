# SIMD headers

This component supplies `usr/include/simd/simd.h` and its Clang module map
to both SDK archives. It covers the vector, matrix, and quaternion types
used by the generated Model I/O headers.

The generator reads C-family declarations from Apple's SIMD DocC pages.
It checks the extended-vector declarations and uses the documented
`columns[4]` and `vector` members to complete the abbreviated matrix and
quaternion records. The Minimal archive records the generator digest,
the pinned snapshot digest, and the exact page URLs in
`c-sdk-provenance.json`.
[SIMD](https://developer.apple.com/documentation/simd) ·
[Matrix members](https://developer.apple.com/documentation/simd/simd_float4x4) ·
[Quaternion members](https://developer.apple.com/documentation/simd/simd_quatf)

`make compose-sdk` runs the component against the prepared snapshot. To
generate the two files alone from a cached copy:

```sh
build/inputs/python/bin/python -m components.simd.generate_headers \
  --cache-dir build/inputs/docc --out build/simd
```

For live development, pass `--fetch-missing` with a development cache.
The [Minimal SDK ABI test](../../tests/minimal_sdk_linking/simd-abi.c)
checks size, alignment, and member offsets.
