# test/test_navier_stokes.jl
#
# Test suite for verifying the Navier-Stokes formulation implementation.
using Test
using Gridap
using SBM_Bioreactor

@testset "Navier-Stokes Weak Form" begin
    # Verify the monolithic Navier-Stokes implementation against standard cases.
    domain = (0, 1, 0, 1)
    partition = (4, 4)
    model = CartesianDiscreteModel(domain, partition)

    # Taylor-Hood Elements: P2 for velocity, P1 for pressure
    reffe_u = ReferenceFE(lagrangian, VectorValue{2, Float64}, 2)
    reffe_p = ReferenceFE(lagrangian, Float64, 1)

    # Test Spaces
    V = TestFESpace(model, reffe_u, conformity=:H1, dirichlet_tags="boundary")
    Q = TestFESpace(model, reffe_p, conformity=:H1, constraint=:zeromean)

    # Zero velocity on all boundaries
    uD(x) = VectorValue(0.0, 0.0)

    # Trial Spaces
    U = TrialFESpace(V, uD)
    P = TrialFESpace(Q)

    Y = MultiFieldFESpace([V, Q])
    X = MultiFieldFESpace([U, P])

    degree = 4
    Ω = Triangulation(model)
    dΩ = Measure(Ω, degree)

    μ = 1.0
    ρ = 1.0
    f(x) = VectorValue(0.0, 0.0)

    # The physics.jl weak form is tested here.
    res_physics(x, y) = ∫( navier_stokes_weak_form(x[1], x[2], y[1], y[2], μ, ρ, f) )dΩ

    op = FEOperator(res_physics, X, Y)

    # Solve the non-linear problem using Newton-Raphson
    using LineSearches: BackTracking
    nls = NLSolver(show_trace=false, method=:newton, linesearch=BackTracking())
    solver = FESolver(nls)
    
    # We need an initial guess for the non-linear solver
    x0 = zeros(num_free_dofs(X))
    xh = FEFunction(X, x0)

    xh, cache = solve!(xh, solver, op)

    uh, ph = xh

    # Test that velocity is essentially zero
    l2(u) = sqrt(sum(∫(u⋅u)dΩ))
    @test l2(uh) < 1e-10
end
