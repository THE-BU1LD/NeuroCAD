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
- Output paths are chosen by the invoking user and may replace an existing file.
- NeuroCAD performs no network requests during generation or validation.
