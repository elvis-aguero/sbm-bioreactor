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
#   - partition=(16,16), up from (10,10); confirmed visually good after a
#     mesh-convergence check against (24,24)/(32,32)/(40,40).
#   - total_time=30s, nsteps=2000. Chosen to comfortably clear both of the
#     model's other two timescales so the field has a chance to reach a
#     repeating/settled pattern rather than a single partial transient:
#     the rotation period (2π/ω ≈ 8.0s at ω=7.5rpm, so this is ~3.75 rotations)
#     and the buoyancy crossing time under the artificial scaling below
#     (domain radius / scaled settling velocity ≈ 50mm / 4.6mm/s ≈ 11s, so
#     this is ~2.7 crossings).
# buoyancy_scale=1e6 is an ARTIFICIAL speed-up, disclosed on the Results slide:
# the real Stokes settling velocity for these particles is ~nm/s (months to
# cross the domain), invisible on any short illustrative clip. Scaling it by
# 1e6 gives a settling velocity of order mm/s -- visible in this clip -- without
# touching the momentum equation's own (real, unscaled) gravity term. This
# affects only this illustration script; every other caller of particle_flux
# still gets the literal, unscaled physical flux (buoyancy_scale defaults to 1.0).
#
# Caveat NOT fixed by any of the above: shear-induced migration (Jsc, Jsμ) was
# never scaled like buoyancy was, and it scales as a² for a=5μm particles --
# a back-of-envelope estimate of its diffusive rate puts the time to visibly
# redistribute Φ over the domain at ~10^8 s (years), not seconds, at ANY
# computationally reasonable total_time. So what settles into a "quasi-steady"
# pattern here is bulk advection (rotation) balanced against artificially-sped
# buoyancy, not migration outrunning/fighting buoyancy -- that competition
# remains physically real but not visually demonstrable on this clip without
# also scaling migration.
using Gridap
using SBM_Bioreactor
include(joinpath(@__DIR__, "visualize.jl"))

println("Building case and running simulation..."); flush(stdout)
case = build_harv_2d_case(partition=(16, 16), dt=0.015, total_time=30.0)
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
# n=31 rendered fast but looked visibly blocky (same "too coarse" complaint as
# the first attempt); n=61 was visually smooth and legible in a direct
# side-by-side comparison against n=45/61/81 -- n=81 was barely different for
# ~1.8x the cost, so not worth it. animate_bare_scalar (see its docstring)
# precomputes point-location once per video rather than once per frame, so
# render cost is now ~seconds total for both videos, not the ~45-55 minutes
# n=61 cost before that fix.
render_n = 61

# Fixed clims across every frame of an animation, not auto-rescaled per frame
# (the default), so color always means the same value throughout the clip --
# otherwise a field that's settling toward uniformity would misleadingly keep
# looking "full contrast" as Plots rescales each frame to its own min/max.
# phi: 0 to the case's default phi_cloud seed value (0.1, unchanged here).
# velocity magnitude: 0 to the wall speed ω·radius, the max speed a
# solid-body-like rotating flow reaches (at the outer wall; zero at center),
# with a small margin for transients.
ω = case.metadata.omega_rpm * 2π / 60.0
clims_phi = (0.0, 0.1)
clims_u = (0.0, 1.1 * ω * case.metadata.radius)

println("Rendering phi.mp4..."); flush(stdout)
animate_bare_scalar(phi_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "phi.mp4"), fps=30, n=render_n, clims=clims_phi)

println("Rendering velocity.mp4..."); flush(stdout)
animate_bare_scalar(u_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "velocity.mp4"), fps=30, n=render_n, post=v -> sqrt(v[1]^2 + v[2]^2), clims=clims_u)

println("VIDEOS_DONE")
