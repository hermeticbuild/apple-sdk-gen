# ApplicationServices

This opt-in macOS umbrella makes the LaunchServices declarations in the
CoreServices profile visible via `<ApplicationServices/ApplicationServices.h>`.
The matching macOS 26.5 Apple OSS distribution has no ApplicationServices
project. The installed macOS 26.5.2 dylibs identify AppKit's reexport of
ApplicationServices and its reexport of CoreServices. The recipe preserves
those relationships when the profiles are selected together. This permits
GLib's existing link line with AppKit and CoreFoundation.
[macOS 26.5 source inventory](https://github.com/apple-oss-distributions/distribution-macOS/tree/83390100289cedfe669c31a96c94326d31afa1ed)

The collocated fixture checks the LaunchServices record layout and calls
the bundle query through the existing AppKit link line. On arm64 and
x86_64 the candidate and Xcode 26.5 both record the checked imports through
CoreServices and execute them on macOS 26.5.2. The Graphics, Text, Image I/O,
and other ApplicationServices reexports are outside this profile.
