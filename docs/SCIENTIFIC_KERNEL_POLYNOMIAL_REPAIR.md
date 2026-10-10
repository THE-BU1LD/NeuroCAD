# Polynomial differentiation repair — 10 October 2026

The second-order `Jet` kernel rejected `x ** 0` and `x ** 1` at `x = 0`, although
both polynomial maps have finite first and second derivatives there. This broke
ordinary polynomial design expressions at zero-valued variables. A boolean
variable index was also accepted by integer comparisons, after which NumPy's
boolean indexing could mark several independent derivative axes simultaneously.
The public differentiation wrapper accepted a returned Jet with the wrong input
dimension.

The kernel now handles constant and identity powers before singular derivative
formulas, validates integer dimensions and indices, and verifies the returned
gradient dimension. Negative/fractional zero powers that the kernel cannot
differentiate remain rejected.

The new regression suite checks analytic monomial value/gradient/Hessian
identities at zero, negative and positive points; composed derivatives; a mixed
polynomial Hessian; malformed index/shape admission; and retained singularity
errors. Run with:

```bash
python -m pytest tests/test_scientific_kernel.py tests/test_scientific_kernel_polynomials.py -q
```

This is a numerical implementation repair. It changes no protected benchmark,
geometry output, CAD provider, compiler contract, historical evidence or research
claim. It establishes these analytic software identities, not physical validity
or external engineering acceptance.
