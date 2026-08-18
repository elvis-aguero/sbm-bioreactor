# Sysimage Plan

- Problem: cold startup dominates first-run solver timings.
- Evidence: blocked `GMRES` cold `32x32` took `266.6 s`.
- Warm solves are already practical after compilation.
- Goal: make notebook and script startup reproducibly fast.

## Scope

- Build one project sysimage for solver workflows.
- Precompile a representative blocked `GMRES` workload.
- Keep runtime behavior unchanged after warmup.

## Workflow

- Build with `julia --project=. scripts/build_sysimage.jl`.
- Launch with `julia --project=. -J artifacts/SBM_Bioreactor_sysimage.<platform-extension>`.
- The build script chooses the correct shared-library extension for the host OS (`.dylib` on macOS, `.so` on Linux).
- Install the notebook kernel with `julia --project=. scripts/install_sysimage_kernel.jl`.
- Then select `Julia SBM Sysimage` inside Jupyter.
- Rebuild after package or solver-signature changes.

## Workload choice

- Use `8x8`, `degree=2`, blocked `GMRES`, explicit `BDF1`.
- Exercise `build_harv_2d_case`.
- Exercise `run_bioreactor_simulation`.
- Avoid VTK and plotting in the precompile workload.

## Success criteria

- Cold first-step startup drops substantially.
- Notebook kernel startup remains stable.
- Warm timings stay unchanged.
