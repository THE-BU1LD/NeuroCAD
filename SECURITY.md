# Security Policy

## Supported version

Only the latest tagged NeuroCAD release receives security fixes. Alpha releases
must not be exposed directly as an unauthenticated network service.

## Reporting a vulnerability

After the repository is public, report vulnerabilities through GitHub's private
security-advisory form for `THE-BU1LD/NeuroCAD`. Do not publish exploit details
in a public issue before a fix is available.

Include the NeuroCAD version, operating system, reproduction command, affected
files, impact, and whether untrusted prompt or artifact input is required.

## Trust boundaries

- Prompt text is treated as untrusted and is sanitized before it is placed in
  generated OpenSCAD comments.
- Feature counts and `$fn` are bounded to prevent unbounded generation.
- OpenSCAD compilation runs as the current local user. Do not compile untrusted
  hand-edited SCAD in a privileged account or in a directory containing secrets.
- CLI export paths reject existing outputs and path collisions by default;
  commands that support replacement require explicit `--force`. The low-level
  atomic-writing Python helpers can replace their caller-selected destination.
- The local workbench binds to loopback, checks Host and Origin headers, rejects
  ambiguous HTTP framing and duplicate JSON keys, bounds request sizes and worker
  count, and serializes kernel compilation. Mesh downloads use short-lived,
  unguessable URLs in bounded process memory. These controls do not provide
  authentication; remote binding requires explicit opt-in and an authenticated
  reverse proxy for any shared service.
- NeuroCAD performs no network requests during generation or validation.
