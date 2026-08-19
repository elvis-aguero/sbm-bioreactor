# scripts/build_sysimage.jl
#
# One-time step: bakes a custom Julia sysimage with SBM_Bioreactor, Gridap, and Plots
# pre-compiled (including the specific method specializations used by
# run_bioreactor_simulation and the visualization helpers), so that later `julia`
# invocations -- even fresh processes started from a shell script -- skip almost all of
# the ~15 minute one-time JIT compilation cost that Gridap's AD-based residual assembly
# otherwise pays on every run.
#
# Usage:
#   julia --project=. scripts/build_sysimage.jl
#
# Then run scripts/tests/notebooks against the sysimage instead of a bare `julia`:
#   julia --project=. --sysimage=sbm_bioreactor.so scripts/run_harv_2d.jl
#
# Rebuild whenever src/ changes meaningfully -- the sysimage is a snapshot, not a
# live link to the package source.

using PackageCompiler

const REPO_ROOT = normpath(joinpath(@__DIR__, ".."))
const SYSIMAGE_PATH = joinpath(REPO_ROOT, "sbm_bioreactor.so")
const PRECOMPILE_FILE = joinpath(@__DIR__, "sysimage_precompile_workload.jl")

create_sysimage(
    [:SBM_Bioreactor, :Gridap, :LineSearches, :Plots];
    sysimage_path=SYSIMAGE_PATH,
    precompile_execution_file=PRECOMPILE_FILE,
    project=REPO_ROOT,
)

println("Sysimage written to $(SYSIMAGE_PATH)")
