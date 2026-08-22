using Gridap
using LineSearches: BackTracking

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
    
    # Time discretization using BDF1 (Backward Euler) or BDF2.
    # x_prevs is always a fixed-shape 2-tuple (see run_bioreactor_simulation) so that
    # this function's argument types never change between order==1 and order==2 steps;
    # letting x_prevs be a 1-tuple on the first step forces Gridap's AD/assembly
    # pipeline to be JIT-compiled a second time from scratch for the new tuple type,
    # roughly doubling the (already expensive) one-time compilation cost.
    u_n, p_n, Φ_n, C_n, Γ_n = x_prevs[1]
    if order == 1
        u_dot = (u - u_n) / dt
        Φ_dot = (Φ - Φ_n) / dt
        C_dot = (C - C_n) / dt
    else
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
    # Defaults to 1.0 (the literal physical flux, unchanged) for every existing
    # caller; only illustrative visualizations set this explicitly. See the note
    # in particle_flux for why it can't just be folded into g.
    buoyancy_scale = get(params, :buoyancy_scale, 1.0)

    # Constitutive Relations: Mixture density and Krieger-Dougherty viscosity
    ρ = (1.0 - Φ) * ρf + Φ * ρs
    visc_op(phi) = krieger_viscosity(phi; μf=μf, Φmax=Φmax)
    μ = visc_op ∘ Φ

    # Analytical gradient of viscosity with respect to Φ (for the migration terms)
    # dμ/dΦ = μf * (-2.5*Φmax) * (1-Φ/Φmax)^(-2.5*Φmax-1) * (-1/Φmax)
    dμ_dΦ_op(phi) = 2.5 * μf * (1.0 - phi/Φmax)^(-2.5*Φmax - 1.0)
    ∇μ = (dμ_dΦ_op ∘ Φ) * ∇(Φ)

    # 1. Shear Rate Projection: Smooth Γ to calculate ∇Γ in the migration flux
    res_gamma = v_γ * (Γ - shear_rate(u))

    # 2. Momentum Balance: Navier Stokes + Hele-Shaw depth-averaged friction
    drag_coeff = 4.0 * μf / (L^2)
    res_ns = (ρ * u_dot ⋅ v) + navier_stokes_weak_form(u, p, v, q, μ, ρ, g, u_wall, drag_coeff)

    # 3. Modified Continuity: ∇⋅u = - ∇⋅(J * (1/ρs - 1/ρf))
    # This accounts for volume changes when particles migrate in a variable density mixture.
    flux = particle_flux(u, Φ, ∇(Φ), μ, ∇μ, a, ρs, ρf, μf, Φavg, g, Γ, ∇(Γ); buoyancy_scale=buoyancy_scale)
    res_continuity_rhs = ∇(q) ⋅ (flux * ((ρs - ρf) / (ρs * ρf)))
    
    # 4. Particle Transport: ∂Φ/∂t + u⋅∇Φ = -∇⋅J + Source
    # Source term models cell proliferation (B.7)
    source_phi = (π/6.0 * a^3) * kc * C * d0 * exp(ke * t)
    res_phi = (w * Φ_dot) + (w * (u ⋅ ∇(Φ))) + (∇(w) ⋅ (flux * ((ρs - ρf) / (ρs * ρf)))) - (w * source_phi)
    
    # 5. Nutrient Transport: Advection-Diffusion-Reaction
    # Consumption rate rc is proportional to cell concentration (Φ / volume_of_one_cell)
    rc = -kc * (Φ / (π/6.0 * a^3))
    res_C = (z * C_dot) + (z * (u ⋅ ∇(C))) + (Df * ∇(z) ⊙ ∇(C)) - (z * rc)
    
    return res_ns + res_continuity_rhs + res_phi + res_C + res_gamma
end

"""
    coupled_bioreactor_jacobian(x, dx, x_prevs, y, dt, params, order=1, t=0.0)

Hand-derived Gateaux derivative of `coupled_bioreactor_residual` in direction `dx`,
tested against `y`. Mirrors the residual term-for-term via ordinary product/quotient/
chain rules (including the second Krieger-Dougherty derivative needed to linearize
∇μ, since ∇μ itself depends on Φ).

Supplying this explicitly to `FEOperator` avoids Gridap's automatic Jacobian, which
would otherwise re-evaluate the entire residual expression tree a second time with
`ForwardDiff.Dual` numbers substituted for `Float64` -- doubling the already-expensive
one-time JIT compilation of this deeply-nested monolithic weak form. Measured on a
tiny (2x2 mesh) case: the AD path's first `jacobian` call takes ~760s (99.7% compile);
this analytic path takes ~214s (99.7% compile) for the same call -- about a 3.5x
reduction. Correctness is checked to machine precision against the AD Jacobian in
test/test_analytic_jacobian.jl; re-run that test after changing any nonlinear term in
this function or in coupled_bioreactor_residual.
"""
function coupled_bioreactor_jacobian(x, dx, x_prevs, y, dt, params, order=1, t=0.0)
    u, p, Φ, C, Γ = x
    du, dp, dΦ, dC, dΓ = dx
    v, q, w, z, v_γ = y

    u_n, p_n, Φ_n, C_n, Γ_n = x_prevs[1]
    if order == 1
        u_dot = (u - u_n) / dt
        du_dot = du / dt
        dΦ_dot = dΦ / dt
        dC_dot = dC / dt
    else
        u_nn, p_nn, Φ_nn, C_nn, Γ_nn = x_prevs[2]
        u_dot = (3.0*u - 4.0*u_n + u_nn) / (2.0*dt)
        du_dot = (3.0*du) / (2.0*dt)
        dΦ_dot = (3.0*dΦ) / (2.0*dt)
        dC_dot = (3.0*dC) / (2.0*dt)
    end

    μf = params.μf
    Φmax = params.Φmax
    a = params.a
    ρs = params.ρs
    ρf = params.ρf
    g = params.g
    Df = params.Df
    Φavg = params.Φavg
    L = params.L
    kc = params.kc
    buoyancy_scale = get(params, :buoyancy_scale, 1.0)

    ρ = (1.0 - Φ) * ρf + Φ * ρs
    dρ = (ρs - ρf) * dΦ

    dμ_dΦ_op(phi) = 2.5 * μf * (1.0 - phi/Φmax)^(-2.5*Φmax - 1.0)
    # Second derivative of the Krieger-Dougherty law, needed because ∇μ = μ'(Φ)∇Φ
    # itself depends on Φ, so linearizing ∇μ requires μ''(Φ) as well.
    dμ2_dΦ2_op(phi) = 2.5 * μf * (2.5*Φmax + 1.0) / Φmax * (1.0 - phi/Φmax)^(-2.5*Φmax - 2.0)
    visc_op(phi) = krieger_viscosity(phi; μf=μf, Φmax=Φmax)

    μ = visc_op ∘ Φ
    μ1 = dμ_dΦ_op ∘ Φ
    μ2 = dμ2_dΦ2_op ∘ Φ
    ∇μ = μ1 * ∇(Φ)
    dμ = μ1 * dΦ
    d∇μ = (μ2 * dΦ * ∇(Φ)) + (μ1 * ∇(dΦ))

    Γ̇ = shear_rate(u)
    dΓ̇ = (2.0 * (ε(u) ⊙ ε(du))) / Γ̇
    res_gamma_jac = v_γ * (dΓ - dΓ̇)

    drag_coeff = 4.0 * μf / (L^2)
    res_ns_jac =
        (dρ * u_dot ⋅ v) + (ρ * du_dot ⋅ v) +
        (dρ * (u ⋅ ∇(u)) ⋅ v) + (ρ * (du ⋅ ∇(u)) ⋅ v) + (ρ * (u ⋅ ∇(du)) ⋅ v) +
        (dμ * (∇(u) ⊙ ∇(v))) + (μ * (∇(du) ⊙ ∇(v))) +
        (-dp * (∇ ⋅ v)) + (q * (∇ ⋅ du)) +
        (drag_coeff * du ⋅ v)

    κ = (ρs - ρf) / (ρs * ρf)

    ∇ΓΦ = Γ * ∇(Φ) + Φ * ∇(Γ)
    d∇ΓΦ = dΓ*∇(Φ) + Γ*∇(dΦ) + dΦ*∇(Γ) + Φ*∇(dΓ)
    dJsc = -0.41 * (a^2) * (dΦ*∇ΓΦ + Φ*d∇ΓΦ)

    ∇lnμ = (1.0/μ) * ∇μ
    d∇lnμ = (d∇μ / μ) - (∇μ * dμ / (μ*μ))
    dJsμ = -0.62 * (a^2) * ((2.0*Φ*dΦ*Γ*∇lnμ) + (Φ*Φ*dΓ*∇lnμ) + (Φ*Φ*Γ*d∇lnμ))

    C1 = 2.0 * a^2 * μf * (1.0 - Φavg) * (ρs - ρf) / 9.0
    h_op(m) = C1 / (m*m)
    h = h_op ∘ μ
    dh = (-2.0 * C1 / (μ*μ*μ)) * dμ
    dJst = -buoyancy_scale * (dΦ * (h*g) + Φ * (dh*g))

    dflux = dJsc + dJsμ + dJst

    res_continuity_rhs_jac = ∇(q) ⋅ (dflux * κ)

    d_source_phi = (π/6.0 * a^3) * kc * params.d0 * exp(params.ke * t) * dC
    res_phi_jac =
        (w * dΦ_dot) + (w * (du ⋅ ∇(Φ))) + (w * (u ⋅ ∇(dΦ))) +
        (∇(w) ⋅ (dflux * κ)) -
        (w * d_source_phi)

    d_rc = -kc * (dΦ / (π/6.0 * a^3))
    res_C_jac =
        (z * dC_dot) + (z * (du ⋅ ∇(C))) + (z * (u ⋅ ∇(dC))) +
        (Df * ∇(z) ⊙ ∇(dC)) -
        (z * d_rc)

    return res_ns_jac + res_continuity_rhs_jac + res_phi_jac + res_C_jac + res_gamma_jac
end

"""
    ResidualProbe(x_prevs, dΩ, dt, params, order, t)

Callable functor wrapping `coupled_bioreactor_residual` for use as `FEOperator`'s
residual argument, in place of an ad-hoc closure. A `struct` is a nominal type: the
same `ResidualProbe` built inside this package's own `@compile_workload` and one built
inside a test file are the exact same type, so the precompiled specialization is
actually reused. A closure defined locally in a test file, by contrast, gets its own
anonymous type distinct from an identically-written closure baked into
`@compile_workload` -- so precompiling that path never helps the test, and Gridap's
AD/assembly machinery gets JIT-compiled from scratch again, every CI run.
"""
struct ResidualProbe{Xp,DΩ,Dt,P} <: Function
    x_prevs::Xp
    dΩ::DΩ
    dt::Dt
    params::P
    order::Int
    t::Float64
end
(f::ResidualProbe)(x, y) = ∫( coupled_bioreactor_residual(x, f.x_prevs, y, f.dt, f.params, f.order, f.t) )f.dΩ

"""
    JacobianProbe(x_prevs, dΩ, dt, params, order, t)

Callable functor wrapping `coupled_bioreactor_jacobian`, analogous to `ResidualProbe`.
"""
struct JacobianProbe{Xp,DΩ,Dt,P} <: Function
    x_prevs::Xp
    dΩ::DΩ
    dt::Dt
    params::P
    order::Int
    t::Float64
end
(f::JacobianProbe)(x, dx, y) = ∫( coupled_bioreactor_jacobian(x, dx, f.x_prevs, y, f.dt, f.params, f.order, f.t) )f.dΩ

"""
    run_bioreactor_simulation(X, Y, dΩ, dt, params, nsteps; write_vtk_interval=1, output_prefix="results", collect_history=false)

Execute the time-stepping loop for the bioreactor simulation using a Newton solver.

# Arguments
- `X`, `Y`: Trial and Test MultiFieldFESpaces.
- `dΩ`: Integration measure.
- `dt`: Time step size.
- `params`: NamedTuple of physical and numerical parameters.
- `nsteps`: Number of time steps.
- `write_vtk_interval`: Frequency of VTK output.
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
)
    # Initial state interpolation
    x_n = interpolate_everywhere([params.u0, params.p0, params.Φ0, params.C0, params.Γ0], X)
    x_nn = x_n # For BDF2, first step fallback to BDF1 logic
    
    # Newton-Raphson solver with BackTracking line search for stability
    nls = NLSolver(show_trace=true, method=:newton, linesearch=BackTracking())
    solver = FESolver(nls)
    
    xh = x_n
    # Newton's solve!(xh, ...) mutates xh's underlying free-dof array in place, so
    # storing xh itself in history would leave every entry aliasing the same buffer
    # (all snapshots collapsing to the final state). Store an independent copy.
    snapshot(x) = FEFunction(X, copy(get_free_dof_values(x)))
    history = collect_history ? Any[snapshot(x_n)] : nothing
    times = collect_history ? Float64[0.0] : nothing

    # res/jac used to close directly over per-step-local x_prevs/order/t, so every
    # step built a brand new FEOperator -- and FEOperator's construction rebuilds
    # the SparseMatrixAssembler (sparsity pattern, Jacobian/residual storage) from
    # scratch, a large FIXED cost paid every step regardless of problem size
    # (measured: allocations/step barely changed between a 1205-dof and a 3077-dof
    # mesh). The residual/Jacobian *forms* -- which fields couple to which -- don't
    # depend on x_prevs/order/t at all, so the sparsity pattern is identical every
    # step; only the numeric values change. Route the varying pieces through this
    # mutable box instead, so `op` (and its assembler) is built once and reused.
    state = Ref((x_prevs=(x_n, x_nn), order=1, t=dt))
    res(x, y) = ∫( coupled_bioreactor_residual(x, state[].x_prevs, y, dt, params, state[].order, state[].t) )dΩ
    jac(x, dx, y) = ∫( coupled_bioreactor_jacobian(x, dx, state[].x_prevs, y, dt, params, state[].order, state[].t) )dΩ
    op = FEOperator(res, jac, X, Y)

    for step in 1:nsteps
        t = step * dt
        println("Step: $step, Time: $t")

        # Use BDF1 for the first step, BDF2 for subsequent steps. x_prevs is always a
        # 2-tuple (x_nn is simply unused when order==1) to keep its type stable across
        # steps -- see the note in coupled_bioreactor_residual.
        order = step == 1 ? 1 : 2
        state[] = (x_prevs=(x_n, x_nn), order=order, t=t)

        # Solve the nonlinear system
        xh, _ = solve!(xh, solver, op)
        
        # Update time-history
        x_nn = x_n
        x_n = xh
        if collect_history
            push!(history, snapshot(xh))
            push!(times, t)
        end
        
        # Diagnostic output
        if write_vtk_interval > 0 && step % write_vtk_interval == 0
            writevtk(get_triangulation(dΩ), "$(output_prefix)_$step", 
                     cellfields=["u"=>xh[1], "p"=>xh[2], "phi"=>xh[3], "C"=>xh[4], "gamma"=>xh[5]])
        end
    end
    
    if collect_history
        return (final_state=xh, history=history, times=times)
    end
    return xh
end
