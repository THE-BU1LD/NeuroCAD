# Bundle output ownership

## Problem and repair

The ordinary generation, enclosure-project and OpenSCAD-exchange paths promise
to publish a new output directory without replacing existing work. Resolving the
entire destination path followed a dangling output symlink, however, and could
write a bundle into that link's previously absent target. Generation and project
publication also used `os.replace`, which could replace an empty directory
created by another writer after the initial admission check. The exchange path
rechecked existence but still had a check-to-rename interval.

The three paths now resolve trusted parent directories while preserving the
output leaf, reject existing leaves including dangling symlinks, and publish via
the existing `publish_directory_noreplace` primitive. That primitive lives in
`core.gmsh_integrity` but has no Gmsh or optional-kernel dependency. Its behavior
is already exercised for native Linux publication, platform dispatch and
competing processes in `tests/test_gmsh_integrity.py`.

On a collision, only the caller's private staging directory is removed; the
other writer's directory, file or symlink remains. New bundles retain their
existing formats, provenance and verification checks. Parent directories remain
trusted; this is an output-ownership guarantee, not a filesystem sandbox or a
power-loss durability guarantee. Platforms or filesystems without the existing
atomic no-replace capability fail closed.

## Verification on 8 October 2026

Base: `main@23c7284048512ca8d956c9a2c4c62eb1f8b8ea89`.

The 18-case regression suite in `tests/test_bundle_publication.py` produced
**5 failures and 13 passes** against the unmodified product source. The five
failures were the three redirected dangling-link exports and the two overwritten
late empty directories. With the repair, **18 passed**. The suite exercises real
source generation and bundle verification, injects competing output creation
after the final manifest write, and checks surviving entry identity/content and
staging cleanup.

The connected product regression command was:

```sh
python -m pytest -q tests/test_bundle_publication.py tests/test_terminal_daemon.py tests/test_enclosure_product.py tests/test_enclosure_cli.py tests/test_integrations.py tests/test_gmsh_integrity.py --tb=short
```

It returned **159 passed, 2 failed**. Both failures occurred when the restricted
local environment refused Unix-socket creation with `PermissionError: [Errno 1]
Operation not permitted`, before daemon communication:

- `test_daemon_runs_durable_generation_job`
- `test_shutdown_acknowledgement_is_flushed_before_server_stops`

Those two tests remain unchanged and require the hosted runner; this is not a
claim that the whole suite passed locally. Ruff, scoped Mypy and compileall passed
for the three changed product files and the new regression file. Local runtime:
Linux x86_64, Python 3.12.14, pytest 9.1.1, NumPy 2.4.1 and trimesh 4.11.3.

This change does not modify the separate STEP-staging path, daemon job listing,
the existing single-file enclosure-publication candidate, or research datasets,
protocols and outcome artifacts. Hosted release checks and review still govern
integration.
