# Physics v2 paper

`main.tex` is the arXiv-oriented source. Its introduction, related work,
contract, methods, threats, and artifact statement were written before the
protected outcome was available. It does not contain confirmatory numbers by
hand.

After the single protected run, generate the result include from the locked
artifacts:

```bash
python paper/physics_v2/generate_results.py \
  --run-dir research/physics_v2/runs/NC-PHYS-V2-CONFIRM-001 \
  --ledger research/physics_v2/CONFIRMATORY_EXECUTION.json \
  --output paper/physics_v2/generated_results.tex
```

The generator refuses a non-confirmatory manifest, a case count other than
216, a non-final execution ledger, or a metrics file whose hash differs from
the ledger. Author identity must be confirmed before submission. The paper's
claims must remain within the controlled software-contract boundary.
