"""
    module SBM_Bioreactor

A Julia package for simulating particle migration and cell growth in bioreactors 
using the Suspension Balance Model (SBM).

The solver implements a monolithic 5-variable finite element formulation (u, p, Φ, C, Γ) 
based on Gridap.jl. It accounts for shear-induced migration, buoyancy-driven 
sedimentation, and Hele-Shaw depth-averaged viscous effects as described in 
Chao & Das (2015).

# Key Features
- Monolithic coupling of Navier-Stokes and particle/nutrient transport.
- Krieger-Dougherty constitutive model for concentration-dependent viscosity.
- Shear-induced migration fluxes (SBM).
- Support for BDF1/BDF2 time stepping.
"""
module SBM_Bioreactor
using Gridap
using PrecompileTools: @compile_workload
using LineSearches: BackTracking

include("physics.jl")
include("examples.jl")
include("solver.jl")

@doc "run_bioreactor_simulation(X, Y, dΩ, dt, params, nsteps; write_vtk_interval=10): Execute the time-dependent SBM simulation." run_bioreactor_simulation
export run_bioreactor_simulation

@doc "build_harv_2d_case(; kwargs...): Construct a tutorial-scale 2D HARV setup for the 5-field solver." build_harv_2d_case
export build_harv_2d_case

@doc "krieger_viscosity(Φ, Φmax): Compute the local fluid viscosity using the Krieger-Dougherty model." krieger_viscosity
export krieger_viscosity

@doc "shear_rate(u): Compute the magnitude of the shear rate tensor for SBM migration." shear_rate
export shear_rate

@doc "particle_flux(u, Φ, gradΦ, params): Compute the particle migration flux combining shear-induced and buoyancy effects." particle_flux
export particle_flux

@doc "navier_stokes_weak_form(u, p, v, q, dΩ, params): Assemble the Navier-Stokes weak form for the bioreactor flow." navier_stokes_weak_form
export navier_stokes_weak_form

@doc "coupled_bioreactor_residual(X, Y, dΩ, params): Compute the monolithic residual for the (u, p, Φ, C) system." coupled_bioreactor_residual
export coupled_bioreactor_residual

@doc "coupled_bioreactor_jacobian(x, dx, x_prevs, y, dt, params, order=1, t=0.0): Hand-derived Jacobian of coupled_bioreactor_residual, avoiding Gridap's automatic (AD) differentiation." coupled_bioreactor_jacobian
export coupled_bioreactor_jacobian

function run_simulation()
    println("Simulation started.")
end

# Bakes the native code for the monolithic residual/Jacobian assembly into this
# package's own precompile cache (Julia's standard package-image mechanism), instead of
# paying that ~5-15 minute one-time JIT cost again on every fresh `julia` process that
# loads SBM_Bioreactor. Exercises both the BDF1 (step 1) and BDF2 (step 2+) branches on
# the smallest possible case, with all diagnostic output suppressed. This is a plain
# package precompile workload -- not a test -- so it runs automatically whenever this
# package's cache needs rebuilding (`Pkg.precompile()`, CI with a cached `~/.julia`
# depot, or a fresh `using SBM_Bioreactor`), with no separate build step to remember.
@compile_workload begin
    case = build_harv_2d_case(partition=(2, 2), dt=0.2, total_time=0.4, degree=4)
    redirect_stdout(devnull) do
        run_bioreactor_simulation(
            case.X, case.Y, case.dΩ, case.metadata.dt, case.params, case.metadata.nsteps;
            write_vtk_interval=0,
        )
    end
end

end
