# Reproduce the frozen Physics v3 conformance study

Read PROTOCOL.md first. freeze.json is already created; do not recreate it or
edit its bound inputs. The scalar study is project-authored formula conformance,
not independent scientific reproduction. Its first result is 31/32 PASS with
one retained opposing-load maximum-stress defect; do not retune the cases.

From the repository root, with a new output directory:

```sh
python3 scripts/validate_physics_v3.py --output /tmp/neurocad-v3-source-new
```

This loads only the stdlib analytical module directly. It does not establish
package installation or end-to-end CLI acceptance. For installed acceptance,
first satisfy the protocol resource guard, build a wheel, create a fresh venv
outside the checkout, install that wheel and run `pip check`. Then:

```sh
python3 scripts/validate_physics_v3.py \
  --installed-python /absolute/path/to/clean-venv/bin/python \
  --output /tmp/neurocad-v3-installed-new
```

The runner refuses changed frozen content and protected inventories, checks
installed source identities and refuses checkout imports. A zero exit status
requires every case and acceptance endpoint to pass. BLOCKED and INVALID are
never PASS. Raw commands, reports, failures and environment identities live in
the requested output directory. Preserve this directory, even after failure.

The `Frozen Physics v3 validation` GitHub workflow builds and installs the
candidate wheel, runs this suite, compiles all four complex shapes, runs the
compatibility tests and retains artifacts even when conformance fails.

Known defect repair must be a separate source revision and separately frozen
successor. A repaired replay of these now-known cases is regression evidence,
not fresh blinded confirmation. Physical experiments, independent execution
and intended-user studies remain separate required evidence.
