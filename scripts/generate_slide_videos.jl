# scripts/generate_slide_videos.jl
#
# One-shot generator for the two synchronized slide-deck videos (particle
# concentration Φ and velocity magnitude) used in slides/slides.md. Both are
# rendered from the same simulation run and the same interpolated frame times,
# so they stay frame-for-frame in sync. See /root/.claude/plans/zippy-imagining-dove.md
# for the parameter choices (4 min simulated time, 100 real solves, interpolated
# to 600 frames for smooth 20s@30fps playback).
using Gridap
using SBM_Bioreactor
include(joinpath(@__DIR__, "visualize.jl"))

println("Building case and running simulation..."); flush(stdout)
case = build_harv_2d_case(partition=(10, 10), dt=2.4, total_time=240.0)
result = run_bioreactor_simulation(
    case.X, case.Y, case.dΩ, case.metadata.dt, case.params, case.metadata.nsteps;
    collect_history=true, write_vtk_interval=0,
)
println("Simulation done, $(length(result.history)) snapshots. Interpolating..."); flush(stdout)

frames, _ = interpolate_history(result.history, result.times, case.X; nframes=600)
phi_frames = [f[3] for f in frames]
velmag_frames = [vector_magnitude(f[1]) for f in frames]

output_dir = joinpath(@__DIR__, "..", "slides", "public")
mkpath(output_dir)

println("Rendering phi.mp4..."); flush(stdout)
animate_bare_scalar(phi_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "phi.mp4"), fps=30)

println("Rendering velocity.mp4..."); flush(stdout)
animate_bare_scalar(velmag_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "velocity.mp4"), fps=30)

println("VIDEOS_DONE")
