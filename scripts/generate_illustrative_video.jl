# scripts/generate_illustrative_video.jl
#
# A second, explicitly-labeled ILLUSTRATIVE slide-deck video pair, complementing
# scripts/generate_slide_videos.jl's realistic clip (real 5μm cells, unscaled
# physics -- shows the true, small buoyancy perturbation on top of near-rigid
# rotation, which is itself a real and important result: it demonstrates why the
# device gives low-shear culture).
#
# This clip instead asks "what would the model predict for a bigger, denser
# tracer particle?" -- a genuinely lab-realizable substitution (e.g. a 1mm
# polymer bead used as a flow tracer), NOT an artificial force-multiplier like
# buoyancy_scale. All physics here is unscaled (buoyancy_scale defaults to 1.0).
#
# Parameter derivation (see chat discussion): the sedimentation-driven Φ
# redistribution speed scales as κ*f_h*u_st, where κ=(ρs-ρf)/ρf. Both κ and u_st
# grow with the density contrast Δρ, so redistribution speed scales as ~Δρ² --a
# much bigger lever than particle size alone. At the paper's real a=5μm, Δρ=50,
# this speed is ~1.4 nm/s (hours-to-days to cross any visible fraction of the
# domain, entirely unwatchable). At a=1mm, Δρ=200 (ρs=1250 vs the default
# ρf=1050 -- still just water-plus-a-bit, not glass or metal), it's ~0.10mm/s:
# full-radius crossing in ~490s, so a 300s (5 min) simulated window gives a
# clearly visible ~61% sweep. The resulting particle Reynolds number is ~1.3e-3
# (Stokes flow assumption solidly intact -- this is not a large-particle regime
# where the model's own hindered-settling formula would stop applying).
#
# ω=2rpm (vs. the realistic clip's 7.5rpm) is deliberately slower: it doesn't
# change the sedimentation speed at all (independent of ω), but it shrinks the
# competing rotational speed enough that the buoyancy-driven velocity deviation
# (~8.3mm/s, from Δρ*ΔΦ*g/drag_coeff) becomes ~80% of the wall speed instead of
# ~1% -- a real, visible "tug of war" between rotation and buoyancy, still with
# 10 full rotations over the 300s window so rotation itself stays legible.
#
# u0 defaults to rest as of the fix to build_harv_2d_case (fluid starts genuinely
# at rest, wall impulsively starts rotating), so this clip also shows the
# ~0.15-0.2s spin-up transient at the very start -- under-resolved at this
# script's dt=0.1s (chosen for the *slow* settling dynamics, not the fast
# transient) into just 1-2 raw simulation steps, but interpolate_history below
# still produces a visible ramp across a handful of video frames rather than a
# single-frame jump.
#
# Playback: 300s of simulated time compressed into a 30s clip (10x speedup,
# disclosed on the Results slide, same honest "time-lapse" framing nature
# documentaries use for slow processes) -- not a hidden manipulation of the
# underlying physics.
using Gridap
using SBM_Bioreactor
include(joinpath(@__DIR__, "visualize.jl"))

println("Building case and running simulation..."); flush(stdout)
case = build_harv_2d_case(partition=(16, 16), omega_rpm=2.0, dt=0.1, total_time=300.0)
params = merge(case.params, (a=1.0e-3, ρs=1250.0))
result = run_bioreactor_simulation(
    case.X, case.Y, case.dΩ, case.metadata.dt, params, case.metadata.nsteps;
    collect_history=true, write_vtk_interval=0,
)
println("Simulation done, $(length(result.history)) snapshots. Interpolating..."); flush(stdout)

frames, _ = interpolate_history(result.history, result.times, case.X; nframes=900)
phi_frames = [f[3] for f in frames]
u_frames = [f[1] for f in frames]

output_dir = joinpath(@__DIR__, "..", "slides", "public")
mkpath(output_dir)

render_n = 61

ω = case.metadata.omega_rpm * 2π / 60.0
clims_phi = (0.0, 0.1)
# 1.5x margin (vs. the realistic clip's 1.1x) since the buoyancy-driven
# deviation is now a much larger fraction of the wall speed, not a small
# perturbation -- a tighter bound would clip the very thing this clip exists
# to show.
clims_u = (0.0, 1.5 * ω * case.metadata.radius)

println("Rendering phi_illustrative.mp4..."); flush(stdout)
animate_bare_scalar(phi_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "phi_illustrative.mp4"), fps=30, n=render_n, clims=clims_phi)

println("Rendering velocity_illustrative.mp4..."); flush(stdout)
animate_bare_scalar(u_frames; radius=case.metadata.radius, output_path=joinpath(output_dir, "velocity_illustrative.mp4"), fps=30, n=render_n, post=v -> sqrt(v[1]^2 + v[2]^2), clims=clims_u)

println("VIDEOS_DONE")
