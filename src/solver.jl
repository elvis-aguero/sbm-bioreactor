using Gridap
import Gridap.Algebra
using LineSearches: BackTracking
using GridapSolvers
using GridapSolvers.LinearSolvers
using GridapSolvers.BlockSolvers

#
# Solver file map
# ----------------
# 1. Constitutive and derivative helpers used by the explicit BDF1 Jacobian.
# 2. Monolithic residual and explicit Jacobian assembly for the 5-field system.
# 3. Operator and linear-solver builders.
# 4. Debug / safety wrappers for blocked Krylov solves.
# 5. Time-stepping driver `run_bioreactor_simulation`.
#
# The core unknown ordering is always `(u, p, Φ, C, Γ)`.
# - `u, p` are the flow variables.
# - `Φ, C` are the transported scalars.
# - `Γ` is a projected shear-rate field introduced to avoid second derivatives
#   in the migration flux terms.
#

# -----------------------------------------------------------------------------
# Constitutive and derivative helpers for the explicit BDF1 Jacobian
# -----------------------------------------------------------------------------

function _supports_explicit_bdf1_case(params, order)
    order == 1 || return false
    get(params, :use_explicit_jacobian, false) || return false
    return true
end

function _get_param(params, name, default)
    hasproperty(params, name) ? getproperty(params, name) : default
end

"""
    _shear_rate_directional_derivative(u, du)

Return the directional derivative of `Γ = shear_rate(u)` in the direction `du`.
"""
function _shear_rate_directional_derivative(u, du)
    shear_arg = 2.0 * ε(u) ⊙ ε(u)
    dshear_arg = 4.0 * ε(u) ⊙ ε(du)
    d_shear_rate_op(x) = sign(x) / (2.0 * sqrt(abs(x) + 1.0e-10))
    return (d_shear_rate_op ∘ shear_arg) * dshear_arg
end

function _one_cell_volume(a)
    return (π / 6.0) * a^3
end

function _krieger_viscosity_derivative(phi, μf, Φmax)
    return 2.5 * μf * (1.0 - phi / Φmax)^(-2.5 * Φmax - 1.0)
end

function _krieger_viscosity_second_derivative(phi, μf, Φmax)
    exponent = -2.5 * Φmax - 2.0
    prefactor = 2.5 * μf * (2.5 * Φmax + 1.0) / Φmax
    return prefactor * (1.0 - phi / Φmax)^exponent
end

"""
    _viscosity_terms(Φ, dΦ, params; freeze_viscosity=false)

Return `(μ, dμ, ∇μ, d∇μ)` for the current concentration field.

When `freeze_viscosity=true`, the constitutive response collapses to constant
`μf`, which is useful for ablations and simpler preconditioner models.
"""
function _viscosity_terms(Φ, dΦ, params; freeze_viscosity=false)
    μf = params.μf
    Φmax = params.Φmax

    if freeze_viscosity
        zero_like = 0.0 * dΦ
        return μf, zero_like, zero_like, zero_like
    end

    visc_op(phi) = krieger_viscosity(phi; μf=μf, Φmax=Φmax)
    dμ_dΦ_op(phi) = _krieger_viscosity_derivative(phi, μf, Φmax)
    d2μ_dΦ2_op(phi) = _krieger_viscosity_second_derivative(phi, μf, Φmax)
    μ = visc_op ∘ Φ
    dμ = (dμ_dΦ_op ∘ Φ) * dΦ
    ∇μ = (dμ_dΦ_op ∘ Φ) * ∇(Φ)
    d∇μ = ((d2μ_dΦ2_op ∘ Φ) * dΦ) * ∇(Φ) + ((dμ_dΦ_op ∘ Φ) * ∇(dΦ))
    return μ, dμ, ∇μ, d∇μ
end

function _sedimentation_velocity_frozen(params)
    a = params.a
    ρs = params.ρs
    ρf = params.ρf
    μf = params.μf
    Φavg = params.Φavg
    return (1.0 - Φavg) * (2.0 * a^2 * (ρs - ρf) / (9.0 * μf)) * params.g
end

"""
    _particle_flux_directional_derivative(Φ, Γ, dΦ, dΓ, params; freeze_viscosity=false)

Linearize the full SBM migration flux with respect to the transport variables
`Φ` and `Γ`.
"""
function _particle_flux_directional_derivative(Φ, Γ, dΦ, dΓ, params; freeze_viscosity=false)
    a = params.a
    ∇ΓΦ = Γ * ∇(Φ) + Φ * ∇(Γ)
    d∇ΓΦ = dΓ * ∇(Φ) + Γ * ∇(dΦ) + dΦ * ∇(Γ) + Φ * ∇(dΓ)
    dJsc = -0.41 * (a^2) * ((dΦ * ∇ΓΦ) + (Φ * d∇ΓΦ))

    if freeze_viscosity
        ust = _sedimentation_velocity_frozen(params)
        dJst = -(ust * dΦ)
        return dJsc + dJst
    end

    μ, dμ, ∇μ, d∇μ = _viscosity_terms(Φ, dΦ, params; freeze_viscosity=false)
    ∇lnμ = (1.0 / μ) * ∇μ
    d∇lnμ = (-(dμ / (μ * μ)) * ∇μ) + ((1.0 / μ) * d∇μ)
    dJsμ = -0.62 * (a^2) * (
        (2.0 * Φ * dΦ * Γ * ∇lnμ) +
        ((Φ * Φ) * dΓ * ∇lnμ) +
        ((Φ * Φ) * Γ * d∇lnμ)
    )

    μf = params.μf
    Φavg = params.Φavg
    ρs = params.ρs
    ρf = params.ρf
    sedimentation_prefactor = μf * (1.0 - Φavg) * (2.0 * a^2 * (ρs - ρf) / 9.0)
    ust = (sedimentation_prefactor / (μ * μ)) * params.g
    dust = ((-2.0 * sedimentation_prefactor * dμ) / (μ * μ * μ)) * params.g
    dJst = -(dust * Φ) - (ust * dΦ)

    return dJsc + dJsμ + dJst
end

function _navier_stokes_convection_jacobian(u, du, v, ρ, dρ)
    convective_state = (u ⋅ ∇(u)) ⋅ v
    return (dρ * convective_state) + (ρ * ((du ⋅ ∇(u)) ⋅ v)) + (ρ * ((u ⋅ ∇(du)) ⋅ v))
end

"""
    _gamma_jacobian_bdf1(u, du, dΓ, v_γ)

Explicit BDF1 Jacobian contribution for the `Γ` projection equation.
"""
function _gamma_jacobian_bdf1(u, du, dΓ, v_γ)
    dshear = _shear_rate_directional_derivative(u, du)
    return v_γ * (dΓ - dshear)
end

"""
    _momentum_jacobian_bdf1(...)

Explicit BDF1 Jacobian block for the momentum / pressure part of the monolithic
system.
"""
function _momentum_jacobian_bdf1(u, p, Φ, du, dp, dΦ, v, q, u_n, dt, params; include_convection=true, freeze_viscosity=false)
    μf = params.μf
    ρs = params.ρs
    ρf = params.ρf
    L = params.L

    ρ = (1.0 - Φ) * ρf + Φ * ρs
    dρ = (ρs - ρf) * dΦ
    μ, dμ, _, _ = _viscosity_terms(Φ, dΦ, params; freeze_viscosity=freeze_viscosity)
    drag_coeff = 4.0 * μf / (L^2)
    u_dot = (u - u_n) / dt
    du_dot = du / dt

    jac = (dρ * (u_dot ⋅ v)) +
          (ρ * (du_dot ⋅ v))

    if include_convection
        jac += _navier_stokes_convection_jacobian(u, du, v, ρ, dρ)
    end

    jac += (dμ * (∇(u) ⊙ ∇(v))) +
           (μ * ∇(du) ⊙ ∇(v)) -
           (dp * (∇ ⋅ v)) +
           (q * (∇ ⋅ du)) +
           (drag_coeff * (du ⋅ v))

    return jac
end

"""
    _continuity_jacobian_bdf1(Φ, Γ, dΦ, dΓ, q, params; ...)

Explicit BDF1 Jacobian block for the modified continuity equation.
"""
function _continuity_jacobian_bdf1(Φ, Γ, dΦ, dΓ, q, params; enable_particle_flux=false, freeze_viscosity=false)
    if !enable_particle_flux
        return 0.0 * (dΦ * q)
    end

    flux_coeff = (params.ρs - params.ρf) / (params.ρs * params.ρf)
    dflux = _particle_flux_directional_derivative(Φ, Γ, dΦ, dΓ, params; freeze_viscosity=freeze_viscosity)
    return ∇(q) ⋅ (dflux * flux_coeff)
end

"""
    _phi_jacobian_bdf1(...)

Explicit BDF1 Jacobian block for the particle volume-fraction equation.
"""
function _phi_jacobian_bdf1(u, Φ, C, Γ, du, dΦ, dC, dΓ, w, u_n, Φ_n, dt, params, t; enable_growth_source=true, enable_particle_flux=false, freeze_viscosity=false)
    _ = u_n
    _ = Φ_n
    a = params.a
    kc = params.kc
    ke = params.ke

    jac = (w * (dΦ / dt)) +
          (w * (du ⋅ ∇(Φ))) +
          (w * (u ⋅ ∇(dΦ)))

    if enable_particle_flux
        flux_coeff = (params.ρs - params.ρf) / (params.ρs * params.ρf)
        dflux = _particle_flux_directional_derivative(Φ, Γ, dΦ, dΓ, params; freeze_viscosity=freeze_viscosity)
        jac += ∇(w) ⋅ (dflux * flux_coeff)
    end

    if enable_growth_source
        source_coeff = _one_cell_volume(a) * kc * params.d0 * exp(ke * t)
        jac -= w * (source_coeff * dC)
    end

    return jac
end

"""
    _nutrient_jacobian_bdf1(...)

Explicit BDF1 Jacobian block for the nutrient transport equation.
"""
function _nutrient_jacobian_bdf1(u, Φ, C, du, dΦ, dC, z, dt, params; enable_nutrient_reaction=true)
    a = params.a
    Df = params.Df

    jac = (z * (dC / dt)) +
          (z * (du ⋅ ∇(C))) +
          (z * (u ⋅ ∇(dC))) +
          (Df * ∇(z) ⊙ ∇(dC))

    if enable_nutrient_reaction
        reaction_coeff = params.kc / _one_cell_volume(a)
        jac += z * (reaction_coeff * dΦ)
    end

    return jac
end

# -----------------------------------------------------------------------------
# Monolithic residual and explicit Jacobian
# -----------------------------------------------------------------------------

"""
    coupled_bioreactor_residual(x, x_prevs, y, dt, params, order=1, t=0.0)

Compute the residual of the monolithic 5-variable system for the SBM bioreactor.

# 5-Variable Formulation (u, p, Φ, C, Γ)
- `u`: Velocity field (Mixture momentum).
- `p`: Pressure field (Continuity/Incompressibility).
- `Φ`: Particle volume fraction (Particle transport).
- `C`: Nutrient concentration (Chemical transport).
- `Γ`: Shear rate (Projected auxiliary variable for smoothing).

# Physical Meaning of Residuals
1. `res_ns`: Navier-Stokes momentum balance with Hele-Shaw drag.
2. `res_continuity_rhs`: Modified continuity equation. In SBM, divergence of velocity 
   is non-zero if there is a net particle flux due to density differences (ρs != ρf).
3. `res_phi`: Particle conservation law including shear-induced migration and 
   cell growth (source term).
4. `res_C`: Nutrient conservation with advection, diffusion, and consumption.
5. `res_gamma`: L2-projection of the shear rate. Treating Γ as a primary variable 
   smoothes the shear-gradient terms in the particle flux.
"""
function coupled_bioreactor_residual(x, x_prevs, y, dt, params, order=1, t=0.0)
    # Unpack trial and test functions
    u, p, Φ, C, Γ = x
    v, q, w, z, v_γ = y
    
    # Time discretization using BDF1 (Backward Euler) or BDF2
    if order == 1
        u_n, p_n, Φ_n, C_n, Γ_n = x_prevs[1]
        u_dot = (u - u_n) / dt
        Φ_dot = (Φ - Φ_n) / dt
        C_dot = (C - C_n) / dt
    else
        u_n, p_n, Φ_n, C_n, Γ_n = x_prevs[1]
        u_nn, p_nn, Φ_nn, C_nn, Γ_nn = x_prevs[2]
        u_dot = (3.0*u - 4.0*u_n + u_nn) / (2.0*dt)
        Φ_dot = (3.0*Φ - 4.0*Φ_n + Φ_nn) / (2.0*dt)
        C_dot = (3.0*C - 4.0*C_n + C_nn) / (2.0*dt)
    end

    # Parameters from the configuration
    μf = params.μf
    Φmax = params.Φmax
    a = params.a
    ρs = params.ρs
    ρf = params.ρf
    g = params.g
    Df = params.Df
    Φavg = params.Φavg
    L = params.L
    u_wall = params.u_wall
    kc = params.kc
    ke = params.ke
    d0 = params.d0
    freeze_viscosity = hasproperty(params, :freeze_viscosity) ? params.freeze_viscosity : false
    enable_particle_flux = hasproperty(params, :enable_particle_flux) ? params.enable_particle_flux : true
    enable_growth_source = hasproperty(params, :enable_growth_source) ? params.enable_growth_source : true
    enable_nutrient_reaction = hasproperty(params, :enable_nutrient_reaction) ? params.enable_nutrient_reaction : true
    include_convection = hasproperty(params, :include_convection) ? params.include_convection : true
    
    # Constitutive Relations: Mixture density and Krieger-Dougherty viscosity
    ρ = (1.0 - Φ) * ρf + Φ * ρs
    if freeze_viscosity
        μ = μf
        ∇μ = 0.0 * ∇(Φ)
    else
        visc_op(phi) = krieger_viscosity(phi; μf=μf, Φmax=Φmax)
        μ = visc_op ∘ Φ
        
        # Analytical gradient of viscosity with respect to Φ (for the migration terms)
        # dμ/dΦ = μf * (-2.5*Φmax) * (1-Φ/Φmax)^(-2.5*Φmax-1) * (-1/Φmax)
        dμ_dΦ_op(phi) = 2.5 * μf * (1.0 - phi/Φmax)^(-2.5*Φmax - 1.0)
        ∇μ = (dμ_dΦ_op ∘ Φ) * ∇(Φ)
    end
    
    # 1. Shear Rate Projection: Smooth Γ to calculate ∇Γ in the migration flux
    res_gamma = v_γ * (Γ - shear_rate(u))

    # 2. Momentum Balance: Navier Stokes + Hele-Shaw depth-averaged friction
    drag_coeff = 4.0 * μf / (L^2)
    res_ns = (ρ * u_dot ⋅ v) + navier_stokes_weak_form(u, p, v, q, μ, ρ, g, u_wall, drag_coeff; include_convection=include_convection)
    
    # 3. Modified Continuity: ∇⋅u = - ∇⋅(J * (1/ρs - 1/ρf))
    # This accounts for volume changes when particles migrate in a variable density mixture.
    flux = enable_particle_flux ? particle_flux(u, Φ, ∇(Φ), μ, ∇μ, a, ρs, ρf, μf, Φavg, g, Γ, ∇(Γ)) : (0.0 * ∇(Φ))
    res_continuity_rhs = ∇(q) ⋅ (flux * ((ρs - ρf) / (ρs * ρf)))
    
    # 4. Particle Transport: ∂Φ/∂t + u⋅∇Φ = -∇⋅J + Source
    # Source term models cell proliferation (B.7)
    source_phi = enable_growth_source ? (π/6.0 * a^3) * kc * C * d0 * exp(ke * t) : 0.0
    res_phi = (w * Φ_dot) + (w * (u ⋅ ∇(Φ))) + (∇(w) ⋅ (flux * ((ρs - ρf) / (ρs * ρf)))) - (w * source_phi)
    
    # 5. Nutrient Transport: Advection-Diffusion-Reaction
    # Consumption rate rc is proportional to cell concentration (Φ / volume_of_one_cell)
    rc = enable_nutrient_reaction ? -kc * (Φ / (π/6.0 * a^3)) : 0.0
    res_C = (z * C_dot) + (z * (u ⋅ ∇(C))) + (Df * ∇(z) ⊙ ∇(C)) - (z * rc)
    
    return res_ns + res_continuity_rhs + res_phi + res_C + res_gamma
end

"""
    coupled_bioreactor_jacobian(x, x_prevs, dx, y, dt, params, order=1, t=0.0)

Compute the explicit weak-form Jacobian for the currently supported easy BDF1 monolithic case.
"""
function coupled_bioreactor_jacobian(x, x_prevs, dx, y, dt, params, order=1, t=0.0)
    _supports_explicit_bdf1_case(params, order) || error(
        "Explicit Jacobian is currently supported only for BDF1 with " *
        "enable_particle_flux=false."
    )

    u, p, Φ, C, Γ = x
    du, dp, dΦ, dC, dΓ = dx
    v, q, w, z, v_γ = y
    u_n, _, Φ_n, C_n, _ = x_prevs[1]

    μf = params.μf
    _ = μf
    include_convection = _get_param(params, :include_convection, true)
    enable_growth_source = _get_param(params, :enable_growth_source, true)
    enable_nutrient_reaction = _get_param(params, :enable_nutrient_reaction, true)
    enable_particle_flux = _get_param(params, :enable_particle_flux, true)
    freeze_viscosity = _get_param(params, :freeze_viscosity, false)

    jac_gamma = _gamma_jacobian_bdf1(u, du, dΓ, v_γ)
    jac_ns = _momentum_jacobian_bdf1(
        u,
        p,
        Φ,
        du,
        dp,
        dΦ,
        v,
        q,
        u_n,
        dt,
        params;
        include_convection=include_convection,
        freeze_viscosity=freeze_viscosity,
    )
    jac_continuity = _continuity_jacobian_bdf1(Φ, Γ, dΦ, dΓ, q, params; enable_particle_flux=enable_particle_flux, freeze_viscosity=freeze_viscosity)
    jac_phi = _phi_jacobian_bdf1(
        u,
        Φ,
        C,
        Γ,
        du,
        dΦ,
        dC,
        dΓ,
        w,
        u_n,
        Φ_n,
        dt,
        params,
        t;
        enable_growth_source=enable_growth_source,
        enable_particle_flux=enable_particle_flux,
        freeze_viscosity=freeze_viscosity,
    )
    jac_C = _nutrient_jacobian_bdf1(u, Φ, C, du, dΦ, dC, z, dt, params; enable_nutrient_reaction=enable_nutrient_reaction)

    return jac_ns + jac_continuity + jac_phi + jac_C + jac_gamma
end

"""
    build_bioreactor_operator(X, Y, dΩ, x_prevs, dt, params, order, t)

Build the finite-element operator for one nonlinear solve at one time level.

This is the switchyard between:
- residual-only operators, which let Gridap differentiate internally, and
- residual + explicit Jacobian operators, which use the hand-coded BDF1 Jacobian.
"""
function build_bioreactor_operator(X, Y, dΩ, x_prevs, dt, params, order, t)
    res(x, y) = ∫(coupled_bioreactor_residual(x, x_prevs, y, dt, params, order, t))dΩ
    if _get_param(params, :use_explicit_jacobian, false)
        _supports_explicit_bdf1_case(params, order) || error(
            "Requested use_explicit_jacobian=true for an unsupported configuration."
        )
        jac(x, dx, y) = ∫(coupled_bioreactor_jacobian(x, x_prevs, dx, y, dt, params, order, t))dΩ
        return FEOperator(res, jac, X, Y)
    end
    return FEOperator(res, X, Y)
end

# -----------------------------------------------------------------------------
# Linear solver builders
# -----------------------------------------------------------------------------

function _supported_transport_solver_kinds()
    return (:lu, :gmres)
end

function _build_flow_linear_solver()
    return LUSolver()
end

"""
    _build_transport_linear_solver(transport_kind; transport_verbose=false)

Construct the current transport-block subsolver used inside the blocked linear
solve path.
"""
function _build_transport_linear_solver(transport_kind::Symbol; transport_verbose::Bool=false)
    if transport_kind == :lu
        return LUSolver()
    elseif transport_kind == :gmres
        return GMRESSolver(
            20;
            Pr=JacobiLinearSolver(),
            maxiter=200,
            atol=1.0e-12,
            rtol=1.0e-8,
            verbose=transport_verbose,
        )
    end
    kinds = join(string.(collect(_supported_transport_solver_kinds())), ", ")
    error("Unsupported transport solver kind: $(transport_kind). Supported kinds: $(kinds)")
end

"""
    _build_block_linear_solver(; transport_kind=:lu, outer_kind=:fgmres, ...)

Construct the current 2x2 blocked linear solver for the algebraic split
`(u,p) | (Φ,C,Γ)`.
"""
function _build_block_linear_solver(;
    transport_kind::Symbol=:lu,
    outer_kind::Symbol=:fgmres,
    outer_verbose::Bool=false,
    transport_verbose::Bool=false,
)
    flow_solver = _build_flow_linear_solver()
    transport_solver = _build_transport_linear_solver(transport_kind; transport_verbose=transport_verbose)
    blocks = [
        LinearSystemBlock() LinearSystemBlock()
        LinearSystemBlock() LinearSystemBlock()
    ]
    coeffs = [
        1.0 1.0
        0.0 1.0
    ]
    preconditioner = BlockTriangularSolver(blocks, [flow_solver, transport_solver], coeffs, :upper)
    if outer_kind == :gmres
        return GMRESSolver(
            20;
            Pr=preconditioner,
            maxiter=100,
            atol=1.0e-12,
            rtol=1.0e-8,
            verbose=outer_verbose,
        )
    elseif outer_kind == :fgmres
        return FGMRESSolver(
            20,
            preconditioner;
            maxiter=100,
            atol=1.0e-12,
            rtol=1.0e-8,
            verbose=outer_verbose,
        )
    else
        error("Unsupported blocked outer solver kind: $outer_kind")
    end
end

# -----------------------------------------------------------------------------
# Debug and safety wrappers for blocked Krylov solves
# -----------------------------------------------------------------------------

function _nonlinear_result_summary(cache)
    hasproperty(cache, :result) || return nothing
    r = getproperty(cache, :result)
    return (
        method = hasproperty(r, :method) ? getproperty(r, :method) : nothing,
        iterations = hasproperty(r, :iterations) ? getproperty(r, :iterations) : nothing,
        x_converged = hasproperty(r, :x_converged) ? getproperty(r, :x_converged) : nothing,
        f_converged = hasproperty(r, :f_converged) ? getproperty(r, :f_converged) : nothing,
        xtol = hasproperty(r, :xtol) ? getproperty(r, :xtol) : nothing,
        ftol = hasproperty(r, :ftol) ? getproperty(r, :ftol) : nothing,
    )
end

function _flatten_debug_values(x)
    if x isa Number
        return Float64[x]
    elseif x isa AbstractArray
        vals = Float64[]
        for xi in x
            append!(vals, _flatten_debug_values(xi))
        end
        return vals
    else
        try
            return _flatten_debug_values(collect(x))
        catch
            return Float64[]
        end
    end
end

function _debug_value_stats(x)
    vals = _flatten_debug_values(x)
    return (
        count = length(vals),
        any_nan = any(isnan, vals),
        any_inf = any(isinf, vals),
        maxabs = isempty(vals) ? 0.0 : maximum(abs, vals),
    )
end

struct DebugLinearSolver{S} <: Algebra.LinearSolver
    solver::S
    label::String
end

struct DebugLinearSolverSS{S,SS} <: Algebra.SymbolicSetup
    solver::S
    ss::SS
end

struct DebugLinearSolverNS{S,NS} <: Algebra.NumericalSetup
    solver::S
    ns::NS
end

struct ZeroedInitialGuessLinearSolver{S} <: Algebra.LinearSolver
    solver::S
end

struct ZeroedInitialGuessLinearSolverSS{S,SS} <: Algebra.SymbolicSetup
    solver::S
    ss::SS
end

struct ZeroedInitialGuessLinearSolverNS{S,NS} <: Algebra.NumericalSetup
    solver::S
    ns::NS
end

function Algebra.symbolic_setup(solver::DebugLinearSolver, A::AbstractMatrix)
    println("debug[$(solver.label)] symbolic_setup(A)=$( _debug_value_stats(A) )")
    return DebugLinearSolverSS(solver, Algebra.symbolic_setup(solver.solver, A))
end

function Algebra.symbolic_setup(solver::DebugLinearSolver, A::AbstractMatrix, x)
    println("debug[$(solver.label)] symbolic_setup(A,x): A=$( _debug_value_stats(A) ) x=$( _debug_value_stats(x) )")
    return DebugLinearSolverSS(solver, Algebra.symbolic_setup(solver.solver, A, x))
end

function Algebra.numerical_setup(ss::DebugLinearSolverSS, A::AbstractMatrix)
    println("debug[$(ss.solver.label)] numerical_setup(A)=$( _debug_value_stats(A) )")
    return DebugLinearSolverNS(ss.solver, Algebra.numerical_setup(ss.ss, A))
end

function Algebra.numerical_setup(ss::DebugLinearSolverSS, A::AbstractMatrix, x)
    println("debug[$(ss.solver.label)] numerical_setup(A,x): A=$( _debug_value_stats(A) ) x=$( _debug_value_stats(x) )")
    return DebugLinearSolverNS(ss.solver, Algebra.numerical_setup(ss.ss, A, x))
end

function Algebra.numerical_setup!(ns::DebugLinearSolverNS, A::AbstractMatrix)
    println("debug[$(ns.solver.label)] numerical_setup!(A)=$( _debug_value_stats(A) )")
    Algebra.numerical_setup!(ns.ns, A)
    return ns
end

function Algebra.numerical_setup!(ns::DebugLinearSolverNS, A::AbstractMatrix, x)
    println("debug[$(ns.solver.label)] numerical_setup!(A,x): A=$( _debug_value_stats(A) ) x=$( _debug_value_stats(x) )")
    Algebra.numerical_setup!(ns.ns, A, x)
    return ns
end

function Algebra.solve!(x::AbstractVector, ns::DebugLinearSolverNS, b::AbstractVector)
    println("debug[$(ns.solver.label)] solve!(before): x=$( _debug_value_stats(x) ) b=$( _debug_value_stats(b) )")
    Algebra.solve!(x, ns.ns, b)
    println("debug[$(ns.solver.label)] solve!(after): x=$( _debug_value_stats(x) )")
    return x
end

"""
    _zero_linear_iterate!(x)

Recursively zero a linear-solver iterate, including blocked vectors.

This helper exists because generic `fill!`-based initialization was insufficient
for some blocked Krylov paths and led to poisoned initial iterates.
"""
function _zero_linear_iterate!(x)
    if x isa AbstractArray
        fill!(x, zero(eltype(x)))
    else
        try
            for blk in x.blocks
                _zero_linear_iterate!(blk)
            end
        catch
            fill!(x, zero(eltype(x)))
        end
    end
    return x
end

function Algebra.symbolic_setup(solver::ZeroedInitialGuessLinearSolver, A::AbstractMatrix)
    return ZeroedInitialGuessLinearSolverSS(solver, Algebra.symbolic_setup(solver.solver, A))
end

function Algebra.symbolic_setup(solver::ZeroedInitialGuessLinearSolver, A::AbstractMatrix, x)
    return ZeroedInitialGuessLinearSolverSS(solver, Algebra.symbolic_setup(solver.solver, A, x))
end

function Algebra.numerical_setup(ss::ZeroedInitialGuessLinearSolverSS, A::AbstractMatrix)
    return ZeroedInitialGuessLinearSolverNS(ss.solver, Algebra.numerical_setup(ss.ss, A))
end

function Algebra.numerical_setup(ss::ZeroedInitialGuessLinearSolverSS, A::AbstractMatrix, x)
    return ZeroedInitialGuessLinearSolverNS(ss.solver, Algebra.numerical_setup(ss.ss, A, x))
end

function Algebra.numerical_setup!(ns::ZeroedInitialGuessLinearSolverNS, A::AbstractMatrix)
    Algebra.numerical_setup!(ns.ns, A)
    return ns
end

function Algebra.numerical_setup!(ns::ZeroedInitialGuessLinearSolverNS, A::AbstractMatrix, x)
    Algebra.numerical_setup!(ns.ns, A, x)
    return ns
end

function Algebra.solve!(x::AbstractVector, ns::ZeroedInitialGuessLinearSolverNS, b::AbstractVector)
    _zero_linear_iterate!(x)
    Algebra.solve!(x, ns.ns, b)
    return x
end

function _history_snapshot(x)
    return deepcopy(x)
end

# -----------------------------------------------------------------------------
# Time-stepping driver
# -----------------------------------------------------------------------------

"""
    run_bioreactor_simulation(X, Y, dΩ, dt, params, nsteps; write_vtk_interval=1, output_prefix="results", collect_history=false, profile_steps=false)

Execute the time-stepping loop for the bioreactor simulation using a Newton solver.

# Arguments
- `X`, `Y`: Trial and Test MultiFieldFESpaces.
- `dΩ`: Integration measure.
- `dt`: Time step size.
- `params`: NamedTuple of physical and numerical parameters.
- `nsteps`: Number of time steps.
- `write_vtk_interval`: Frequency of VTK output.

# Notes For Contributors
- This driver owns time stepping and solver orchestration only.
- The PDE itself lives in `coupled_bioreactor_residual`.
- The explicit BDF1 linearization lives in `coupled_bioreactor_jacobian`.
- The blocked linear-algebra path is selected here, but assembled in
  `_build_block_linear_solver`.
"""
function run_bioreactor_simulation(
    X,
    Y,
    dΩ,
    dt,
    params,
    nsteps;
    write_vtk_interval=1,
    output_prefix="results",
    collect_history=false,
    profile_steps=false,
    nonlinear_method=:newton,
    nonlinear_iterations=1000,
    nonlinear_show_trace=true,
    nonlinear_xtol=0.0,
    nonlinear_ftol=1.0e-8,
    nonlinear_autoscale=false,
    max_order=2,
    blocked_linear_solver=false,
    transport_block_solver=:lu,
    blocked_outer_solver=:fgmres,
    blocked_linear_outer_verbose=false,
    blocked_transport_verbose=false,
    blocked_linear_debug=false,
)
    # Initial state interpolation
    x_n = nothing
    initial_setup_time = @elapsed begin
        x_n = interpolate_everywhere([params.u0, params.p0, params.Φ0, params.C0, params.Γ0], X)
    end
    if profile_steps
        println("profile: initial_setup_time=$(round(initial_setup_time, digits=3)) s")
    end
    x_nn = x_n # For BDF2, first step fallback to BDF1 logic
    
    nls_kwargs = (
        show_trace = nonlinear_show_trace,
        method = nonlinear_method,
        iterations = nonlinear_iterations,
        xtol = nonlinear_xtol,
        ftol = nonlinear_ftol,
        autoscale = nonlinear_autoscale,
    )
    ls = blocked_linear_solver ?
        _build_block_linear_solver(;
            transport_kind=transport_block_solver,
            outer_kind=blocked_outer_solver,
            outer_verbose=blocked_linear_outer_verbose,
            transport_verbose=blocked_transport_verbose,
        ) :
        BackslashSolver()
    if blocked_linear_debug
        ls = DebugLinearSolver(ls, "blocked")
    end
    if blocked_linear_solver
        ls = ZeroedInitialGuessLinearSolver(ls)
    end
    nls = nonlinear_method == :newton ?
        NLSolver(ls; nls_kwargs..., linesearch=BackTracking()) :
        NLSolver(ls; nls_kwargs...)
    solver = FESolver(nls)
    
    xh = x_n
    history = collect_history ? Any[_history_snapshot(x_n)] : nothing
    times = collect_history ? Float64[0.0] : nothing
    step_profiles = profile_steps ? NamedTuple[] : nothing
    
    for step in 1:nsteps
        t = step * dt
        println("Step: $step, Time: $t")
        
        # Use BDF1 for the first step, BDF2 for subsequent steps
        order = min(step == 1 ? 1 : 2, max_order)
        x_prevs = order == 1 ? (x_n,) : (x_n, x_nn)
        
        # Define the residual on the triangulation
        op = nothing
        op_build_time = @elapsed begin
            op = build_bioreactor_operator(X, Y, dΩ, x_prevs, dt, params, order, t)
        end
        if profile_steps
            println("profile: step=$(step) operator_build_time=$(round(op_build_time, digits=3)) s")
        end
        
        # Solve the nonlinear system
        solve_result = nothing
        solve_cache = nothing
        solve_time = @elapsed begin
            solve_result = solve!(xh, solver, op)
        end
        solve_cache = solve_result[2]
        if profile_steps
            println("profile: step=$(step) solve_time=$(round(solve_time, digits=3)) s")
        end
        xh, _ = solve_result
        nonlinear_summary = profile_steps ? _nonlinear_result_summary(solve_cache) : nothing
        if profile_steps && !isnothing(nonlinear_summary)
            println("profile: step=$(step) nonlinear=$(nonlinear_summary)")
        end
        
        # Update time-history
        x_nn = x_n
        x_n = xh
        if collect_history
            push!(history, _history_snapshot(xh))
            push!(times, t)
        end
        
        # Diagnostic output
        vtk_time = 0.0
        if write_vtk_interval > 0 && step % write_vtk_interval == 0
            vtk_time = @elapsed begin
                writevtk(get_triangulation(dΩ), "$(output_prefix)_$step",
                         cellfields=["u"=>xh[1], "p"=>xh[2], "phi"=>xh[3], "C"=>xh[4], "gamma"=>xh[5]])
            end
        end
        if profile_steps && vtk_time > 0
            println("profile: step=$(step) vtk_time=$(round(vtk_time, digits=3)) s")
        end

        if profile_steps
            push!(step_profiles, (
                step = step,
                time = t,
                order = order,
                operator_build_time = op_build_time,
                solve_time = solve_time,
                vtk_time = vtk_time,
                nonlinear = nonlinear_summary,
            ))
        end
    end
    
    if collect_history
        if profile_steps
            return (
                final_state = xh,
                history = history,
                times = times,
                profile = (
                    initial_setup_time = initial_setup_time,
                    steps = step_profiles,
                ),
            )
        end
        return (final_state=xh, history=history, times=times)
    end
    if profile_steps
        return (
            final_state = xh,
            profile = (
                initial_setup_time = initial_setup_time,
                steps = step_profiles,
            ),
        )
    end
    return xh
end
