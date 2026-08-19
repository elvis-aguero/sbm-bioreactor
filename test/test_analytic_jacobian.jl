# test/test_analytic_jacobian.jl
#
# coupled_bioreactor_jacobian is a hand-derived Gateaux derivative, supplied to
# FEOperator instead of letting Gridap differentiate the residual automatically (see
# the docstring in src/solver.jl for why: AD roughly triples the one-time JIT-compile
# cost of this monolithic residual). A hand derivation is easy to get subtly wrong, so
# this checks it against Gridap's own AD Jacobian -- ground truth -- to machine
# precision, on both the BDF1 (order=1) and BDF2 (order=2) branches.
using Test
using Gridap
using Gridap.FESpaces: jacobian
using LinearAlgebra
using SBM_Bioreactor

@testset "Analytic Jacobian matches AD Jacobian to machine precision" begin
    case = build_harv_2d_case(partition=(2, 2), dt=0.2, total_time=0.4, degree=4)
    X, Y, dΩ, params = case.X, case.Y, case.dΩ, case.params
    dt = case.metadata.dt

    x_n = interpolate_everywhere([params.u0, params.p0, params.Φ0, params.C0, params.Γ0], X)

    # A generic, non-degenerate state: perturb away from the initial condition (which
    # has exact zeros in parts of Φ) so every term in the Jacobian is actually exercised.
    perturb = Float64[isodd(i) ? 0.7 : 1.3 for i in 1:num_free_dofs(X)]
    x0 = FEFunction(X, get_free_dof_values(x_n) .* perturb .+ 1.0e-3)

    for order in (1, 2)
        x_prevs = (x_n, x_n)
        t = dt

        res(x, y) = ∫( coupled_bioreactor_residual(x, x_prevs, y, dt, params, order, t) )dΩ
        jac_analytic(x, dx, y) = ∫( coupled_bioreactor_jacobian(x, dx, x_prevs, y, dt, params, order, t) )dΩ

        op_ad = FEOperator(res, X, Y)
        op_analytic = FEOperator(res, jac_analytic, X, Y)

        A_ad = jacobian(op_ad, x0)
        A_analytic = jacobian(op_analytic, x0)

        rel_err = norm(A_ad - A_analytic) / norm(A_ad)
        @test rel_err < 1e-8
    end
end
