# scripts/generate_slide_videos.jl
#
# One-shot generator for the two synchronized slide-deck videos (particle
# concentration Φ and velocity magnitude) used in slides/slides.md. Both are
# rendered from the same simulation run and the same interpolated frame times,
# so they stay frame-for-frame in sync.
#
# Parameters, locked in after diagnosing the first (too-coarse, visually-frozen)
# attempt against the model's own timescales (Chao & Das 2015 + Table 1):
#   - dt=0.015s vs. the Hele-Shaw drag relaxation time τ≈0.04s (was 2.4s, ~60x
#     too coarse to resolve that transient at all) -- honestly resolves the one
#     fast physical process in the model instead of aliasing past it.
#   - partition=(16,16), up from (10,10), for a visibly smoother field.
#   - total_time=1.5s (nsteps=100, same real-solve budget as before).
# buoyancy_scale=1e6 is an ARTIFICIAL speed-up, disclosed on the Results slide:
# the real Stokes settling velocity for these particles is ~nm/s (months to
# cross the domain), invisible on any short illustrative clip. Scaling it by
# 1e6 gives a settling velocity of order mm/s -- visible in ~1.5s -- without
# touching the momentum equation's own (real, unscaled) gravity term. This
# affects only this illustration script; every other caller of particle_flux
# still gets the literal, unscaled physical flux (buoyancy_scale defaults to 1.0).
using Gridap
using SBM_Bioreactor
include(joinpath(@__DIR__, "visualize.jl"))

println("Building case and running simulation..."); flush(stdout)
case = build_harv_2d_case(partition=(16, 16), dt=0.015, total_time=1.5)
params = merge(case.params, (buoyancy_scale=1.0e6,))
result = run_bioreactor_simulation(
    case.X, case.Y, case.dΩ, case.metadata.dt, params, case.metadata.nsteps;
    collect_history=true, write_vtk_interval=0,
)
println("Simulation done, $(length(result.history)) snapshots. Interpolating..."); flush(stdout)

frames, _ = interpolate_history(result.history, result.times, case.X; nframes=600)
phi_frames = [f[3] for f in frames]
u_frames = [f[1] for f in frames]

output_dir = joinpath(@__DIR__, "..", "slides", "public")
mkpath(output_dir)

# n=61 for rendering only (the FE solve above stays at the fine partition=(16,16)
# mesh -- this just controls the raster resolution of the sampled heatmap).
# Measured directly: sampling a CellField costs ~0.6-0.8ms *per point* in
# Gridap's evaluate machinery, independent of API tricks (see
# sample_scalar_field's docstring) -- n=121 (14641 points/frame) meant ~9s/frame
# and a ~3 hour render for both videos combined. n=31 rendered in minutes but
# looked visibly blocky (same "too coarse" complaint as the first attempt);
# n=61 (~2.2-2.3s/frame, ~45-55 min for both videos) was visually smooth and
# legible in a direct side-by-side comparison against n=45/61/81 -- n=81 was
# barely different from n=61 for ~1.8x the cost, so not worth it.
render_n = 61

println("Rendering phi.mp4..."); flush(stdout)
animate_bare_scalar(phi_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "phi.mp4"), fps=30, n=render_n)

println("Rendering velocity.mp4..."); flush(stdout)
animate_bare_scalar(u_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "velocity.mp4"), fps=30, n=render_n, post=v -> sqrt(v[1]^2 + v[2]^2))

println("VIDEOS_DONE")
