## Add a version

1. Find the intended Apple [source release](https://opensource.apple.com/releases/)
   and resolve its exact distribution tag to a commit. Read that commit's
   `release.json`, `.gitmodules` and Git tree without checking out the projects
   recursively. Take each selected project's commit from its gitlink.
2. Include only projects required by the recipes. The `projects` map records
   the checkout name, URL, full commit SHA, tag for provenance, and why that
   pin was selected. A `selection` of `distribution` means the pin matches
   the recorded distribution snapshot. Explain standalone releases and
   overrides in that field.
3. Record the reference SDK's canonical name, platform, version and build
   in `sdk`. Prepare, install and run `make test` for the new lock. Use the
   [SDK review workflow](SKILL.md) to check reference
   coverage. Qualify a new platform's install rules and target environments
   before enabling it in the source-lock tool.
