# Immutable harness security review

The first integrated CI scan retained 39 LOW-severity, HIGH-confidence Bandit
1.9.4 findings in six frozen developer harness files. No dependency advisory,
medium/high finding, shell=True call or product-service finding was reported.
The complete failed job is retained under the work-closure receipt.

Every finding was reviewed: subprocess imports, fixed Git/vm_stat argument
vectors, operator-selected isolated Python invocations, and seeded numerical
reference RNG. They run in a trusted development/CI environment. None uses a
shell, builds executable text from model output, generates a security token or
handles untrusted network requests. PATH/tool ownership remains an operator
assumption; this review does not authorize running these tools under a hostile
PATH or supplying an untrusted Python interpreter.

Because these scripts are hash-frozen evidence, adding inline nosec comments
would destroy their recorded identities. Instead the complete unfiltered Bandit
report is retained and matched against FROZEN_HARNESS_REVIEW.json. Each allowed
finding binds its exact path, line, rule and complete source SHA-256. Any new or
missing finding, changed source, severity/confidence change, duplicate or scanner
error fails. All files and rules remain scanned. Regression tests exercise these
failure paths. No global rule or severity threshold was disabled.

This is an implementation security review, not an independent penetration test
or security certification. Future edits require a new explicit review.
