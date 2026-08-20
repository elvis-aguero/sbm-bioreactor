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

        # Built via ResidualProbe/JacobianProbe (structs, i.e. nominal types) rather
        # than local closures -- a closure defined here would get its own anonymous
        # type distinct from an identically-written closure in the package's
        # @compile_workload, so the precompiled AD/analytic specializations built there
        # would never actually be reused here. These probes are the same type either
        # way, so they are.
        res_probe = ResidualProbe(x_prevs, dΩ, dt, params, order, t)
        jac_probe = JacobianProbe(x_prevs, dΩ, dt, params, order, t)

        println("  [test_analytic_jacobian] order=$order: building AD operator..."); flush(stdout)
        op_ad = FEOperator(res_probe, X, Y)
        op_analytic = FEOperator(res_probe, jac_probe, X, Y)

        println("  [test_analytic_jacobian] order=$order: computing AD jacobian..."); flush(stdout)
        A_ad = jacobian(op_ad, x0)
        println("  [test_analytic_jacobian] order=$order: computing analytic jacobian..."); flush(stdout)
        A_analytic = jacobian(op_analytic, x0)

        rel_err = norm(A_ad - A_analytic) / norm(A_ad)
        @test rel_err < 1e-8
    end
end
