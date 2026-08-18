# Transport Preconditioner Roadmap

## Why This Exists

- The outer blocked `GMRES` path is now viable and should stay stable.
- The current flow block is not the next experimental target.
- The unresolved question is inside the transport block.
- `Φ` is the only transport variable that directly changes flow coefficients.
- `Γ` does not belong in the flow block, but it strongly affects migration.
- That makes the next safe refinement a transport-side split, not a flow rewrite.
- Version 1 tests whether `Γ | (Φ,C)` is strong enough.
- If it is not, the fallback is `(Γ,Φ) | C`.

## Goal

- [x] Keep the outer blocked `GMRES` path unchanged.
- [x] Keep the current flow `LU` path unchanged.
- [x] Preserve rollback safety by adding only new transport modes.
- [ ] Implement `transport_nested_gamma_phic_v1`.
- [ ] Benchmark it on the falsification set.
- [ ] Decide stop/go before changing the flow block.

## Version 1 Scope

- [x] Keep the outer split `(u,p) | (Φ,C,Γ)`.
- [x] Keep the outer form upper-triangular.
- [x] Keep full-physics explicit `BDF1` as the target operator.
- [ ] Split the transport block as `Γ | (Φ,C)`.
- [ ] Use cheap `Γ` inversion first.
- [ ] Use an iterative reduced `(Φ,C)` solve with lagged coefficients.
- [ ] Keep `Φ-C` reaction/source coupling in the reduced solve.

## Explicit Deferrals

- [x] Do not change the outer Schur approximation yet.
- [x] Do not replace flow `LU` yet.
- [x] Do not add new physics terms.
- [x] Do not move to `BDF2` yet.
- [x] Do not change the default solver path yet.

## Required KPIs

- [ ] Log outer Krylov iterations.
- [ ] Log inner transport iterations.
- [ ] Log transport solve wall time separately.
- [ ] Log total linear solve wall time.
- [ ] Log one live nonlinear-step outcome.

## Falsification Set

- [ ] Warm `64x64` full-physics linear probe.
- [ ] Warm `128x128` full-physics linear probe.
- [ ] One live first-step full-physics nonlinear probe.

## Stop/Go Rule

- [ ] Go only if `64x64` and `128x128` are robust.
- [ ] Go only if iteration growth is modest.
- [ ] Go only if the live nonlinear step is no worse.
- [ ] Stop if inner transport work explodes.
- [ ] Stop if the nested path only hides a weaker transport solve.

## Fallback

- [ ] If `Γ | (Φ,C)` fails, switch to `(Γ,Φ) | C`.
