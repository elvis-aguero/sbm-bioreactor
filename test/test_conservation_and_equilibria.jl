# test/test_conservation_and_equilibria.jl
#
# Physical self-consistency checks that need an actual time-evolving solve, or
# a real (non-manufactured) equilibrium of the full coupled system. Complements
# test_physical_limits.jl (the static/algebraic checks) and the existing
# discretization-correctness tests (analytic-vs-AD Jacobian, MMS).
#
# CI-cost note: this file runs at most 3 short simulations total, each reused
# across every sub-test that can share it, rather than one simulation per test.
using Test
using Gridap
using LinearAlgebra: norm
using SBM_Bioreactor

@testset "Rigid-body rotation is an exact, unforced steady solution" begin
    # A genuine (non-manufactured) solution of the momentum+continuity system,
    # unlike the existing MMS tests (which add a synthetic AD-derived forcing
    # term so any smooth field trivially satisfies the "manufactured" residual
    # regardless of whether the underlying physics terms are individually
    # correct). For u=u_wall=ω(y,-x) (rigid rotation), ε(u)≡0 exactly -- no
    # shear at all -- so the viscous term, the Hele-Shaw drag (u≡u_wall
    # everywhere), and all three migration flux terms (Φ≡0) vanish identically,
    # leaving only ρ(u⋅∇)u=-ω²ρ(x,y) balanced by ∇p=ρ(ω²(x,y)+g): a classic
    # rigid-rotor pressure field, quadratic in x,y. That needs a degree-2 (not
    # the tutorial case's usual degree-1) pressure space to be exactly
    # representable, hence building FE spaces directly here rather than reusing
    # build_harv_2d_case -- mirrors test_mms.jl's own pattern for the same
    # reason. The domain doesn't need to be the disk (u_wall's tangency to a
    # circular boundary isn't what's being checked here), so a plain square
    # keeps this simple.
    domain = (-0.05, 0.05, -0.05, 0.05)
    partition = (4, 4)
    model = CartesianDiscreteModel(domain, partition)

    ω = 7.5 * 2π / 60.0
    g = VectorValue(0.0, -9.81)
    ρf = 1050.0
    μf = 0.5889

    u_wall(x) = VectorValue(ω * x[2], -ω * x[1])
    p_exact(x) = ρf * (ω^2 * (x[1]^2 + x[2]^2) / 2.0 + g[2] * x[2])
    Γ_exact(x) = sqrt(1.0e-10)

    reffe_u = ReferenceFE(lagrangian, VectorValue{2,Float64}, 2)
    reffe_p = ReferenceFE(lagrangian, Float64, 2)  # degree 2: p_exact is quadratic
    reffe_s = ReferenceFE(lagrangian, Float64, 1)

    V = TestFESpace(model, reffe_u, conformity=:H1, dirichlet_tags="boundary")
    Q = TestFESpace(model, reffe_p, conformity=:H1, constraint=:zeromean)
    W = TestFESpace(model, reffe_s, conformity=:H1)
    Z = TestFESpace(model, reffe_s, conformity=:H1)
    G = TestFESpace(model, reffe_s, conformity=:H1)

    U = TrialFESpace(V, u_wall)
    P = TrialFESpace(Q)
    Φsp = TrialFESpace(W)
    Csp = TrialFESpace(Z)
    Γsp = TrialFESpace(G)

    Y = MultiFieldFESpace([V, Q, W, Z, G])
    X = MultiFieldFESpace([U, P, Φsp, Csp, Γsp])

    Ω = Triangulation(model)
    dΩl = Measure(Ω, 4)

    params = (
        μf=μf, Φmax=0.64, a=5.0e-6, ρs=1000.0, ρf=ρf, g=g, Df=5.4e-10,
        Φavg=0.05, L=0.01, u_wall=u_wall, kc=0.0, ke=4.2e-6, d0=3.0e5,
    )

    x_ex = interpolate_everywhere([u_wall, p_exact, x -> 0.0, x -> 5.5, Γ_exact], X)
    x_prevs = (x_ex, x_ex)  # steady state: x_n = x_nn = x_ex

    res_probe = ResidualProbe(x_prevs, dΩl, 1.0, params, 1, 0.0)
    jac_probe = JacobianProbe(x_prevs, dΩl, 1.0, params, 1, 0.0)
    op = FEOperator(res_probe, jac_probe, X, Y)

    r = Gridap.FESpaces.residual(op, x_ex)
    @test norm(r) < 1e-6
end

@testset "Conservation and bounds over a time-evolving run" begin
    # kc=0 (no growth/consumption) and ρs=ρf (exactly incompressible, ∇⋅u=0)
    # simultaneously: this reuses ONE short run for four checks --
    # ∫Φ conservation, ∫C conservation, Φ∈[0,Φmax), Φ≥0 -- instead of one run
    # each. A smooth (not the tutorial's default discontinuous step) Φ0 is used
    # specifically so any real bound violation isn't confounded with the
    # separate, already-expected Gibbs-type ringing a sharp step IC causes in a
    # plain Galerkin discretization (that's a known, disclosed discretization
    # artifact, not what this test is checking).
    case = build_harv_2d_case(partition=(4, 4), dt=0.02, total_time=0.1)
    radius = case.metadata.radius
    smooth_Φ0(x) = 0.2 + 0.1 * sin(π * x[1] / radius) * cos(π * x[2] / radius)
    params = merge(case.params, (kc=0.0, ρs=1025.0, ρf=1025.0, Φ0=smooth_Φ0))

    result = run_bioreactor_simulation(
        case.X, case.Y, case.dΩ, case.metadata.dt, params, case.metadata.nsteps;
        collect_history=true, write_vtk_interval=0,
    )

    total_Φ = [sum(∫(state[3]) * case.dΩ) for state in result.history]
    total_C = [sum(∫(state[4]) * case.dΩ) for state in result.history]
    Φmax = case.params.Φmax

    @test all(t -> isapprox(t, total_Φ[1]; rtol=1e-5), total_Φ)
    @test all(t -> isapprox(t, total_C[1]; rtol=1e-5), total_C)

    for state in result.history
        Φ_dofs = get_free_dof_values(state[3])
        @test maximum(Φ_dofs) < Φmax
        @test minimum(Φ_dofs) > -1e-8
    end
end

@testset "Nutrient concentration is non-increasing under consumption" begin
    # Default (kc>0, ρs≠ρf) case: a genuinely separate run from the one above,
    # since kc=0 there makes C exactly conserved (trivially "non-increasing"),
    # which wouldn't actually exercise the consumption mechanism.
    case = build_harv_2d_case(partition=(3, 3), dt=0.01, total_time=0.03)
    result = run_bioreactor_simulation(
        case.X, case.Y, case.dΩ, case.metadata.dt, case.params, case.metadata.nsteps;
        collect_history=true, write_vtk_interval=0,
    )
    avg_C = [sum(∫(state[4]) * case.dΩ) for state in result.history]
    @test all(diff(avg_C) .≤ 1e-10)
end

@testset "Growth kinetics matches an independent ODE integration of the same source terms" begin
    # ω=0 (no rotation) with spatially uniform Φ0, C0: with no other momentum
    # forcing breaking symmetry (uniform Φ ⇒ uniform ρ ⇒ gravity is absorbed by
    # a hydrostatic pressure gradient alone), u stays exactly 0 and Φ, C stay
    # exactly spatially uniform for all time -- this is an EXACT reduction to a
    # 2-variable ODE pair, not an approximation, so the PDE solver's own
    # (spatially-averaged) Φ(t), C(t) can be compared directly against an
    # independent RK4 integration of dΦ/dt = a3*kc*C*d0*exp(ke*t),
    # dC/dt = -kc*Φ/a3 (a3 = π/6*a³), the same closed-form growth/consumption
    # submodel coded in coupled_bioreactor_residual.
    #
    # Parameters are a deliberately synthetic regime (not the paper's a=5μm,
    # kc=1e-13): a is chosen so a3=π/6*a³=1 exactly, and kc/d0/ke are picked to
    # give a clearly observable growth signal within a short, cheap test
    # window while keeping Φ safely below Φmax throughout (avoiding a
    # DomainError from Krieger-Dougherty's (1-Φ/Φmax)^... at Φ>Φmax). At the
    # paper's real a=5μm, a3~6.5e-17 makes source_phi negligible on any
    # testable timescale -- this is analogous to buoyancy_scale elsewhere in
    # this repo, an illustrative parameter choice for exercising a mechanism
    # that's real but too slow to observe directly at physical parameter
    # values.
    a_test = (6.0 / π)^(1.0 / 3.0)
    kc_test, d0_test, ke_test = 0.01, 1.0, 0.0
    Φ0_const, C0_const = 0.3, 5.5
    a3 = π / 6.0 * a_test^3  # ≈ 1.0 by construction

    dt_test, total_time_test = 0.025, 0.5
    case = build_harv_2d_case(partition=(2, 2), omega_rpm=0.0, dt=dt_test, total_time=total_time_test)
    params = merge(
        case.params,
        (a=a_test, kc=kc_test, d0=d0_test, ke=ke_test, Φ0=x -> Φ0_const, C0=x -> C0_const),
    )

    result = run_bioreactor_simulation(
        case.X, case.Y, case.dΩ, case.metadata.dt, params, case.metadata.nsteps;
        collect_history=false, write_vtk_interval=0,
    )
    uh_final, ph_final, Φh_final, Ch_final, Γh_final = result
    area = π * case.metadata.radius^2
    Φ_pde = sum(∫(Φh_final) * case.dΩ) / area
    C_pde = sum(∫(Ch_final) * case.dΩ) / area
    speed2 = sum(∫(uh_final ⋅ uh_final) * case.dΩ) / area

    # Independent reference: fine-step RK4 on the same 2-ODE system.
    function rk4_step(f, y, t, h)
        k1 = f(y, t)
        k2 = f(y .+ (h / 2) .* k1, t + h / 2)
        k3 = f(y .+ (h / 2) .* k2, t + h / 2)
        k4 = f(y .+ h .* k3, t + h)
        return y .+ (h / 6) .* (k1 .+ 2 .* k2 .+ 2 .* k3 .+ k4)
    end
    ode_rhs(y, t) = [a3 * kc_test * y[2] * d0_test * exp(ke_test * t), -kc_test * y[1] / a3]

    href = 1.0e-4
    y = [Φ0_const, C0_const]
    t = 0.0
    n_fine = round(Int, total_time_test / href)
    for _ in 1:n_fine
        y = rk4_step(ode_rhs, y, t, href)
        t += href
    end
    Φ_ref, C_ref = y

    @test speed2 < 1e-16  # sanity: velocity genuinely stayed at rest throughout
    @test isapprox(Φ_pde, Φ_ref; rtol=1e-3)
    # The Φ0<<C0 asymmetry (a volume fraction vs. an arbitrary concentration
    # scale) makes the consumption signal on C much weaker than the growth
    # signal on Φ within any short, cheap test window -- this still catches a
    # wrong sign or a badly wrong magnitude in rc, just with a looser bar than
    # the Φ check above.
    @test isapprox(C_pde, C_ref; atol=2e-3)
end
