# scripts/sysimage_precompile_workload.jl
#
# Exercised by PackageCompiler.create_sysimage (see scripts/build_sysimage.jl) to force
# JIT compilation of the real code paths into a custom sysimage, instead of paying that
# cost again on every fresh `julia` invocation.
#
# Runs a tiny end-to-end case through both the BDF1 (step 1) and BDF2 (step 2+) branches
# of coupled_bioreactor_residual -- these are Gridap's most expensive AD/assembly
# compiles by far -- plus the plotting/animation helpers used by the tutorial notebook.

using SBM_Bioreactor
using Gridap
using Plots
using LineSearches: BackTracking

ENV["GKSwstype"] = "100"

include(joinpath(@__DIR__, "visualize.jl"))

case = build_harv_2d_case(partition=(2, 2), dt=0.2, total_time=0.4, degree=4)

result = run_bioreactor_simulation(
    case.X, case.Y, case.dΩ, case.metadata.dt, case.params, case.metadata.nsteps;
    collect_history=true, write_vtk_interval=0,
)

phi_history = [state[3] for state in result.history]

mktempdir() do dir
    plot_harv_mesh(case)
    plot_initial_conditions(case)
    plot_scalar_history_snapshots(phi_history, result.times; radius=case.metadata.radius, colorbar_title="Φ", label="Φ")
    animate_scalar_history(phi_history, result.times; radius=case.metadata.radius,
        output_path=joinpath(dir, "warmup.gif"), fps=2, colorbar_title="Φ", label="Φ")
end
