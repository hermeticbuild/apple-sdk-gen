# libresolv

The C installation takes Apple's four public headers from the pinned
`libresolv` target. It stages the same `nameser.h` bytes at both public
paths. Apple's install script creates a symlink there. Libc supplies
`arpa/nameser_compat.h`.

The full SDK builds the linker stub using the resolver recipe in
[HermeticBuild’s Apple SDK Gen fork](https://github.com/hermeticbuild/apple-sdk-gen).
