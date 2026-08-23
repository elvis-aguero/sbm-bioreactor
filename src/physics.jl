"""
    navier_stokes_weak_form(u, p, v, q, μ, ρ, f, u_drag=nothing, drag_coeff=0.0)

Compute the weak form of the incompressible Navier-Stokes equations with an optional 
Hele-Shaw depth-averaged friction term (B.6 in Chao & Das 2015).

# Arguments
- `u`, `p`: Trial velocity and pressure fields.
- `v`, `q`: Test velocity and pressure fields.
- `μ`: Dynamic viscosity (typically depends on particle concentration Φ).
- `ρ`: Mixture density.
- `f`: Gravitational acceleration (e.g., `g`) -- NOT pre-multiplied by density; this
  function does that internally (Chao & Das 2015 Eq. 1: `ρ ∂u/∂t + ρ(u⋅∇)u = ... + ρg`,
  the last term being force per volume, not the bare acceleration).
- `u_drag`: Reference velocity for drag (e.g., wall velocity).
- `drag_coeff`: Friction coefficient for depth-averaged flow.

# Physical Meaning
1. `(ρ * (u ⋅ ∇(u)) ⋅ v)`: Inertial term (convection of momentum).
2. `(μ * ∇(u) ⊙ ∇(v))`: Viscous stress term (dissipation).
3. `-(p * (∇ ⋅ v))`: Pressure gradient term.
4. `(q * (∇ ⋅ u))`: Continuity constraint (incompressibility).
5. `-(ρ * f ⋅ v)`: Body force term (buoyancy/gravity, force per volume = ρg).
6. `(drag_coeff * (u - u_drag) ⋅ v)`: Hele-Shaw drag representing the out-of-plane
   viscous resistance in thin-gap bioreactors.
"""
function navier_stokes_weak_form(u, p, v, q, μ, ρ, f, u_drag=nothing, drag_coeff=0.0)
    # Standard Navier-Stokes terms: Advection + Diffusion - Pressure + Divergence Constraint - Forces
    #
    # The body force is ρ*f (force per volume), not bare f: f=g is a spatially
    # uniform acceleration, and a spatially uniform force is always exactly
    # absorbable into a hydrostatic pressure gradient with zero effect on velocity,
    # regardless of how Φ (hence ρ) varies. Only a density-weighted force can
    # actually drive buoyancy flow when ρ varies in space -- using bare f here
    # would silently make buoyancy-driven convection impossible for any Φ field.
    #
    # `(f ⋅ v) * ρ`, not `ρ * f ⋅ v`: f is typically a bare constant VectorValue
    # or a plain Julia Function (not a Gridap CellField) at call sites -- Gridap's
    # operator overloading lifts it when combined with the CellField `v` via `⋅`,
    # but `ρ * f` alone (two non-CellField operands whenever ρ happens to be a
    # plain Number, e.g. in the unit test that exercises this in isolation) has no
    # such overload and errors. Scaling the already-lifted `f ⋅ v` result by ρ
    # afterward works in both the scalar-ρ and CellField-ρ cases.
    res = (ρ * (u ⋅ ∇(u)) ⋅ v) + (μ * ∇(u) ⊙ ∇(v)) - (p * (∇ ⋅ v)) + (q * (∇ ⋅ u)) - ((f ⋅ v) * ρ)
    
    # Hele-Shaw Depth-Averaged Friction (B.6)
    # Models the viscous drag from the top and bottom plates in a 2D depth-averaged simulation.
    if u_drag !== nothing && drag_coeff > 0.0
        res = res + (drag_coeff * (u - u_drag) ⋅ v)
    end
    
    return res
end

"""
    krieger_viscosity(Φ; μf=0.5889, Φmax=0.64)

Calculate the effective mixture viscosity using the Krieger-Dougherty empirical relation.

# Arguments
- `Φ`: Local particle volume fraction.
- `μf`: Viscosity of the suspending fluid (base fluid).
- `Φmax`: Maximum packing fraction where viscosity diverges (typically ~0.64 for spheres).

# Physical Meaning
Viscosity increases nonlinearly with particle concentration, becoming infinite as Φ 
approaches Φmax, reflecting the transition from a fluid-like to a solid-like state.
"""
function krieger_viscosity(Φ; μf=0.5889, Φmax=0.64)
    Φc = _clamp_Φ(Φ, Φmax)
    return μf * (1 - Φc/Φmax)^(-2.5*Φmax)
end

# Plain Galerkin FEM on advection-dominated Φ transport (no flux limiter/stabilization)
# can produce bounded but real over/undershoot past [0, Φmax) -- confirmed while
# generating scripts/generate_illustrative_video.jl, where Φ's DOF values drifted to
# -0.09 over a long, rotation-heavy run with strong migration/sedimentation forcing,
# well outside any IC- or timestep-specific edge case. Without this, a fractional
# power of a negative (or >Φmax) base throws a DomainError and aborts the whole
# simulation. Clamping only the *input* to this and the two derivative functions below
# is a purely defensive domain-validity safeguard, not a change to the physics for any
# well-resolved simulation, where Φ already stays in-bounds -- it's identical to
# krieger_viscosity's exact formula for every Φ every existing test exercises.
_clamp_Φ(Φ, Φmax) = clamp(Φ, 0.0, Φmax - 1.0e-9)

"""
    krieger_viscosity_dΦ(Φ; μf=0.5889, Φmax=0.64)

Analytic derivative dμ/dΦ of `krieger_viscosity`, used to build ∇μ = μ'(Φ)∇Φ in
the migration flux and in `coupled_bioreactor_jacobian`'s linearization of ∇μ.
Exported (rather than kept as a solver-local closure) so it can be tested
directly against `krieger_viscosity` itself instead of being duplicated by hand
in two places with nothing checking they still agree.
"""
function krieger_viscosity_dΦ(Φ; μf=0.5889, Φmax=0.64)
    Φc = _clamp_Φ(Φ, Φmax)
    return 2.5 * μf * (1.0 - Φc/Φmax)^(-2.5*Φmax - 1.0)
end

"""
    krieger_viscosity_d2Φ2(Φ; μf=0.5889, Φmax=0.64)

Second derivative d²μ/dΦ² of `krieger_viscosity`. Needed because ∇μ itself
depends on Φ, so linearizing ∇μ for the analytic Jacobian requires μ''(Φ) too.
"""
function krieger_viscosity_d2Φ2(Φ; μf=0.5889, Φmax=0.64)
    Φc = _clamp_Φ(Φ, Φmax)
    return 2.5 * μf * (2.5*Φmax + 1.0) / Φmax * (1.0 - Φc/Φmax)^(-2.5*Φmax - 2.0)
end

"""
    shear_rate(u)

Compute the local shear rate (scalar invariant of the strain rate tensor).

# Arguments
- `u`: Velocity field.

# Physical Meaning
The shear rate Γ = sqrt(2 * ε(u) : ε(u)) quantifies the intensity of local fluid 
deformation, which drives the shear-induced migration of particles.
"""
function shear_rate(u)
    sqrt_op(x) = sqrt(abs(x) + 1e-10) # Regularized square root to avoid singularity at zero
    return sqrt_op ∘ (2.0 * ε(u) ⊙ ε(u))
end

"""
    particle_flux(u, Φ, ∇Φ, μ, ∇μ, a, ρs, ρf, μf, Φavg, g, Γ, ∇Γ)

Compute the total particle migration flux based on the Suspension Balance Model (SBM).

# Arguments
- `u`, `Φ`, `∇Φ`: Velocity, volume fraction, and its gradient.
- `μ`, `∇μ`: Mixture viscosity and its gradient.
- `a`: Particle radius.
- `ρs`, `ρf`: Particle and fluid densities.
- `μf`: Fluid viscosity.
- `Φavg`: Average volume fraction (used in sedimentation hindrance).
- `g`: Gravity vector.
- `Γ`, `∇Γ`: Local shear rate and its gradient.

# Physical Meaning (Chao & Das 2015)
1. `Jsc = -0.41 * a^2 * Φ * ∇(ΓΦ)`: Shear-induced migration from high to low shear 
   and concentration gradients (particle-particle collisions).
2. `Jsμ = -0.62 * a^2 * Φ^2 * Γ * ∇ln(μ)`: Migration toward lower viscosity regions.
3. `Jst = - (ust) * Φ`: Sedimentation flux due to buoyancy, corrected for hindrance 
   effects at high Φ.
"""
function particle_flux(u, Φ, ∇Φ, μ, ∇μ, a, ρs, ρf, μf, Φavg, g, Γ, ∇Γ; buoyancy_scale=1.0)
    # Gradient of log-viscosity for the Jsμ term
    ∇lnμ = (1.0 / μ) * ∇μ

    # Total gradient of (Γ * Φ) for the Jsc term: ∇(Γ*Φ) = Γ*∇Φ + Φ*∇Γ
    ∇ΓΦ = Γ * ∇Φ + Φ * ∇Γ

    # 1. Flux due to shear rate and concentration gradients (Chao & Das Eq. 12)
    Jsc = -0.41 * (a^2) * Φ * ∇ΓΦ

    # 2. Flux due to viscosity gradients (Chao & Das Eq. 13)
    Jsμ = -0.62 * (a^2) * (Φ * Φ) * Γ * ∇lnμ

    # 3. Sedimentation / Buoyancy flux (Chao & Das Eq. 14)
    # Corrected for fluid viscosity and hindrance via Richardson-Zaki like term.
    # buoyancy_scale defaults to 1.0 (the literal physical flux, unchanged from
    # before) -- it exists only so illustrative visualizations can artificially
    # speed up settling (physically ~nm/s for micron-scale near-neutrally-buoyant
    # particles, i.e. months to cross a few cm) without touching the momentum
    # equation's own (real, unscaled) gravity term, which shares the same `g`.
    ust_fh_op(m) = (μf * (1.0 - Φavg) / m) * (2.0 * a^2 * (ρs - ρf) / (9.0 * m)) * g
    Jst = -buoyancy_scale * (ust_fh_op ∘ μ) * Φ

    return Jsc + Jsμ + Jst
end


