# Scientific Regression Environment

This directory holds slower scientific regression tests that should not be required for every edit loop.

## Purpose

These tests compare compact, interpretable numerical summaries against checked-in baselines so that solver changes can be reviewed critically.

## Recommended usage

Run from the repository root:

```bash
julia --project=test/regression test/regression/runtests.jl
```

## Baseline policy

- Prefer compact JSON summaries over full raw fields.
- Update baselines only when solver changes are intentional and scientifically justified.
- Treat baseline changes as reviewable scientific changes, not routine noise.
