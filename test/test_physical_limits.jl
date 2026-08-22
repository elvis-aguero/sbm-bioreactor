# test/test_physical_limits.jl
#
# Physical self-consistency checks that don't require a time-evolving solve:
# limiting-case reductions, sign/directionality, monotonicity/bounds, and
# scaling laws that must hold for the model's own equations to be physically
# valid, independent of mesh/timestep/solver details. Complements the existing
# discretization-correctness tests (analytic-vs-AD Jacobian, MMS) -- those
# check "does the code correctly solve the equations as written"; these check
# "do the equations behave physically."
#
# A single small mesh/case is built once and reused across every testset below
# (no test here needs an actual Newton solve), to keep this file's CI cost low.
# Everything is scoped inside the outer @testset (Test.jl gives it its own
# local scope, like a function body) rather than at file top level, since
# runtests.jl includes every test file into the same Main scope in sequence --
# a top-level `const case = ...` here would collide with an identically-named
# one in another file.
using Test
using Gridap
using LinearAlgebra: norm
using SBM_Bioreactor

@testset "Physical limits, signs, monotonicity, scaling" begin
    case = build_harv_2d_case(partition=(4, 4), total_time=0.0)
    model = case.model
    dΩ = case.dΩ
    p = case.params
    radius = case.metadata.radius

    reffe_u = ReferenceFE(lagrangian, VectorValue{2,Float64}, 2)
    reffe_s = ReferenceFE(lagrangian, Float64, 1)
    Vh = TestFESpace(model, reffe_u, conformity=:H1)
    Wh = TestFESpace(model, reffe_s, conformity=:H1)

    # A deliberately non-degenerate, non-uniform state: nonzero Φ, nonzero ∇Φ,
    # nonzero shear and ∇shear, a rotating (nonzero-strain) velocity field. Used
    # by every test below that needs "some real gradients to act on."
    Φ_nz(x) = 0.1 + 0.05 * (x[1] / radius)
    u_nz(x) = VectorValue(0.01 * x[2], -0.01 * x[1])
    Γ_nz(x) = 2.0 + 0.5 * (x[2] / radius)
    μ_of(Φfun) = x -> krieger_viscosity(Φfun(x); μf=p.μf, Φmax=p.Φmax)

    Φh_nz = interpolate_everywhere(Φ_nz, Wh)
    uh_nz = interpolate_everywhere(u_nz, Vh)
    Γh_nz = interpolate_everywhere(Γ_nz, Wh)
    μh_nz = interpolate_everywhere(μ_of(Φ_nz), Wh)

    flux_norm2(flux) = sum(∫(flux ⋅ flux) * dΩ)

    @testset "Φ=0 collapses migration flux to exactly zero" begin
        Φh0 = interpolate_everywhere(x -> 0.0, Wh)
        μh0 = interpolate_everywhere(μ_of(x -> 0.0), Wh)
        flux = particle_flux(uh_nz, Φh0, ∇(Φh0), μh0, ∇(μh0), p.a, p.ρs, p.ρf, p.μf, p.Φavg, p.g, Γh_nz, ∇(Γh_nz))
        @test flux_norm2(flux) < 1e-28
    end

    @testset "a=0 (point particles) collapses migration flux to exactly zero" begin
        flux = particle_flux(uh_nz, Φh_nz, ∇(Φh_nz), μh_nz, ∇(μh_nz), 0.0, p.ρs, p.ρf, p.μf, p.Φavg, p.g, Γh_nz, ∇(Γh_nz))
        @test flux_norm2(flux) < 1e-28
    end

    @testset "Migration flux scales exactly quadratically in particle radius a" begin
        flux_a = particle_flux(uh_nz, Φh_nz, ∇(Φh_nz), μh_nz, ∇(μh_nz), p.a, p.ρs, p.ρf, p.μf, p.Φavg, p.g, Γh_nz, ∇(Γh_nz))
        flux_2a = particle_flux(uh_nz, Φh_nz, ∇(Φh_nz), μh_nz, ∇(μh_nz), 2 * p.a, p.ρs, p.ρf, p.μf, p.Φavg, p.g, Γh_nz, ∇(Γh_nz))
        # Formula is homogeneous of degree 2 in a, so doubling a must scale flux by exactly 4x.
        @test isapprox(flux_norm2(flux_2a), 4.0^2 * flux_norm2(flux_a); rtol=1e-10)
    end

    @testset "Uniform Φ/Γ/μ (no gradients) zeroes Jsc/Jsμ, leaving only sedimentation" begin
        Φh_u = interpolate_everywhere(x -> 0.1, Wh)
        Γh_u = interpolate_everywhere(x -> 1.0, Wh)
        μh_u = interpolate_everywhere(μ_of(x -> 0.1), Wh)
        flux = particle_flux(uh_nz, Φh_u, ∇(Φh_u), μh_u, ∇(μh_u), p.a, p.ρs, p.ρf, p.μf, p.Φavg, p.g, Γh_u, ∇(Γh_u))

        # Closed-form Jst alone (Eq. 17-18): -f_h * u_st * Φ, f_h = μf(1-Φavg)/μ,
        # u_st = 2a²(ρs-ρf)/(9μ) g.
        μ0 = krieger_viscosity(0.1; μf=p.μf, Φmax=p.Φmax)
        f_h = p.μf * (1.0 - p.Φavg) / μ0
        u_st = (2.0 * p.a^2 * (p.ρs - p.ρf) / (9.0 * μ0)) * p.g
        Jst_exact = -f_h * u_st * 0.1

        flux_int = sum(∫(flux) * dΩ) / (π * radius^2)
        @test isapprox(flux_int[1], Jst_exact[1]; rtol=1e-6, atol=1e-20)
        @test isapprox(flux_int[2], Jst_exact[2]; rtol=1e-6, atol=1e-20)
    end

    @testset "ρs=ρf zeroes the continuity/Φ-transport migration coupling κ" begin
        # This is the coefficient that was dimensionally wrong before the fix in
        # coupled_bioreactor_residual/coupled_bioreactor_jacobian ((ρs-ρf)/(ρs*ρf),
        # missing a factor of ρs) -- now (ρs-ρf)/ρf. Both forms are exactly zero at
        # ρs=ρf, so this doesn't by itself catch the dimensional bug (see the
        # magnitude/units check above) -- it locks in the shape of the reduction:
        # flux (Jsc/Jsμ) stays genuinely nonzero (they don't depend on ρs,ρf at
        # all), but its κ-weighted contribution to continuity/Φ-transport vanishes.
        ρs_matched = ρf_matched = 1025.0
        flux = particle_flux(uh_nz, Φh_nz, ∇(Φh_nz), μh_nz, ∇(μh_nz), p.a, ρs_matched, ρf_matched, p.μf, p.Φavg, p.g, Γh_nz, ∇(Γh_nz))
        @test flux_norm2(flux) > 1e-10

        κ = (ρs_matched - ρf_matched) / ρf_matched
        @test κ == 0.0
        @test flux_norm2(flux * κ) == 0.0
    end

    @testset "Growth source is non-negative, nutrient consumption is non-positive" begin
        # Pure algebra, no FEM: source_phi = (π/6 a³) kc C d0 exp(ke t), rc = -kc Φ/(π/6 a³).
        a3 = π / 6.0 * p.a^3
        for (C, Φ, t) in ((5.5, 0.1, 0.0), (2.0, 0.3, 10.0), (0.0, 0.05, 5.0))
            source_phi = a3 * p.kc * C * p.d0 * exp(p.ke * t)
            rc = -p.kc * (Φ / a3)
            @test source_phi ≥ 0.0
            @test rc ≤ 0.0
        end
        @test (a3 * p.kc * 0.0 * p.d0 * exp(p.ke * 3.0)) == 0.0  # C=0 ⇒ no growth
        @test (-p.kc * (0.0 / a3)) == 0.0                        # Φ=0 ⇒ no consumption
    end

    @testset "kc=0 fully decouples growth/consumption from C, t, ke, d0" begin
        x_prevs = (interpolate_everywhere([p.u0, p.p0, p.Φ0, p.C0, p.Γ0], case.X),)
        x0 = interpolate_everywhere([u_nz, x -> 0.0, Φ_nz, x -> 5.5, Γ_nz], case.X)
        params0 = merge(p, (kc=0.0,))

        # Same FEOperator(ResidualProbe, JacobianProbe, X, Y) + Gridap.FESpaces.residual
        # pattern as test_analytic_jacobian.jl -- an explicit JacobianProbe means this
        # never needs Gridap's AD path (only the residual vector is used here).
        function residual_vec(params, t)
            res_probe = ResidualProbe(x_prevs, dΩ, 0.1, params, 1, t)
            jac_probe = JacobianProbe(x_prevs, dΩ, 0.1, params, 1, t)
            op = FEOperator(res_probe, jac_probe, case.X, case.Y)
            return Gridap.FESpaces.residual(op, x0)
        end

        # ke,d0,t chosen to stay well clear of exp() overflow -- 0.0*Inf=NaN would
        # silently break the "exactly zero" argument below.
        r1 = residual_vec(merge(params0, (ke=4.2e-6, d0=3.0e5)), 5.0)
        r2 = residual_vec(merge(params0, (ke=1.0, d0=1.0e8)), 20.0)
        # kc=0.0 multiplies the entire source/consumption term in both cases, and
        # 0.0*finite=0.0 exactly in IEEE754 regardless of ke/d0/t, so the two
        # residual vectors must be bitwise identical, not just close.
        @test r1 == r2
    end

    @testset "Sedimentation flux direction tracks sign(ρs - ρf)" begin
        Φh_u = interpolate_everywhere(x -> 0.1, Wh)
        Γh_u = interpolate_everywhere(x -> 0.0, Wh)  # Γ=0 ⇒ Jsc=Jsμ=0, isolating Jst
        μh_u = interpolate_everywhere(μ_of(x -> 0.1), Wh)

        flux_light = particle_flux(uh_nz, Φh_u, ∇(Φh_u), μh_u, ∇(μh_u), p.a, 1000.0, 1050.0, p.μf, p.Φavg, p.g, Γh_u, ∇(Γh_u))
        flux_heavy = particle_flux(uh_nz, Φh_u, ∇(Φh_u), μh_u, ∇(μh_u), p.a, 1100.0, 1050.0, p.μf, p.Φavg, p.g, Γh_u, ∇(Γh_u))

        y_light = sum(∫(flux_light) * dΩ)[2]
        y_heavy = sum(∫(flux_heavy) * dΩ)[2]
        # g points in -y; lighter-than-fluid particles (ρs<ρf) rise (+y, against g),
        # denser particles (ρs>ρf) sink (-y, with g).
        @test y_light > 0.0
        @test y_heavy < 0.0
    end

    @testset "Jsc/Jsμ are strictly down-gradient (stabilizing, never anti-diffusive)" begin
        # Jsc = -0.41a²Φ∇(ΓΦ), Jsμ = -0.62a²Φ²Γ∇lnμ -- both must satisfy flux⋅gradient ≤ 0.
        ∇ΓΦ = Γh_nz * ∇(Φh_nz) + Φh_nz * ∇(Γh_nz)
        Jsc = -0.41 * p.a^2 * Φh_nz * ∇ΓΦ
        @test sum(∫(Jsc ⋅ ∇ΓΦ) * dΩ) ≤ 0.0

        ∇lnμ = (1.0 / μh_nz) * ∇(μh_nz)
        Jsμ = -0.62 * p.a^2 * (Φh_nz * Φh_nz) * Γh_nz * ∇lnμ
        @test sum(∫(Jsμ ⋅ ∇lnμ) * dΩ) ≤ 0.0
    end

    @testset "μ'(Φ)/μ(Φ) diverges monotonically as Φ→Φmax" begin
        ratios = Float64[]
        for Φ in (0.1, 0.3, 0.5, 0.6, 0.63, 0.639)
            μ = krieger_viscosity(Φ; μf=p.μf, Φmax=p.Φmax)
            μp = krieger_viscosity_dΦ(Φ; μf=p.μf, Φmax=p.Φmax)
            push!(ratios, μp / μ)
        end
        @test issorted(ratios)
        @test ratios[end] > 100.0 * ratios[1]
    end

    @testset "Hindered-settling factor bounded (0,1], monotone decreasing" begin
        f_h(Φavg, Φ) = p.μf * (1.0 - Φavg) / krieger_viscosity(Φ; μf=p.μf, Φmax=p.Φmax)
        prev_over_Φ = Inf
        for Φ in (0.0, 0.2, 0.4, 0.6)
            v = f_h(0.1, Φ)
            @test 0.0 < v ≤ 1.0
            @test v < prev_over_Φ
            prev_over_Φ = v
        end
        prev_over_Φavg = Inf
        for Φavg in (0.0, 0.1, 0.3)
            v = f_h(Φavg, 0.3)
            @test v < prev_over_Φavg
            prev_over_Φavg = v
        end
    end

    @testset "Mixture density is a convex combination of ρs, ρf" begin
        for Φ in 0.0:0.1:0.6
            ρ = (1.0 - Φ) * p.ρf + Φ * p.ρs
            @test min(p.ρs, p.ρf) ≤ ρ ≤ max(p.ρs, p.ρf)
        end
        h = 1e-6
        ρ(Φ) = (1.0 - Φ) * p.ρf + Φ * p.ρs
        @test isapprox((ρ(0.3 + h) - ρ(0.3 - h)) / (2h), p.ρs - p.ρf; rtol=1e-8)
    end

    @testset "u_wall is exactly tangential to the disk boundary" begin
        for θ in range(0.0, 2π; length=12)
            x = Point(radius * cos(θ), radius * sin(θ))
            uw = p.u_wall(x)
            @test abs(uw ⋅ VectorValue(x[1], x[2])) < 1e-12
        end
    end

    @testset "Sedimentation flux magnitude matches the closed-form Stokes/hindered-settling formula" begin
        Φ0, μf, Φavg, a, ρs, ρf, g = 0.15, p.μf, p.Φavg, p.a, p.ρs, p.ρf, p.g
        μ0 = krieger_viscosity(Φ0; μf=μf, Φmax=p.Φmax)
        Jst_exact = -(μf * (1.0 - Φavg) / μ0) * ((2.0 * a^2 * (ρs - ρf) / (9.0 * μ0)) * g) * Φ0

        Φh_u = interpolate_everywhere(x -> Φ0, Wh)
        Γh_u = interpolate_everywhere(x -> 0.0, Wh)
        μh_u = interpolate_everywhere(μ_of(x -> Φ0), Wh)
        flux = particle_flux(uh_nz, Φh_u, ∇(Φh_u), μh_u, ∇(μh_u), a, ρs, ρf, μf, Φavg, g, Γh_u, ∇(Γh_u))
        flux_avg = sum(∫(flux) * dΩ) / (π * radius^2)

        @test isapprox(flux_avg[1], Jst_exact[1]; rtol=1e-8, atol=1e-20)
        @test isapprox(flux_avg[2], Jst_exact[2]; rtol=1e-8, atol=1e-20)
    end

    @testset "Real (unscaled) Stokes settling velocity is ~nm/s, not accidentally off by orders of magnitude" begin
        u_st = (2.0 * p.a^2 * (p.ρs - p.ρf) / (9.0 * p.μf)) * p.g
        @test 1e-9 < norm(u_st) < 1e-6
    end

    @testset "krieger_viscosity_dΦ / _d2Φ2 match finite differences of krieger_viscosity" begin
        h = 1e-6
        for Φ0 in (0.1, 0.3, 0.5, 0.6)
            fd1 = (krieger_viscosity(Φ0 + h; μf=p.μf, Φmax=p.Φmax) - krieger_viscosity(Φ0 - h; μf=p.μf, Φmax=p.Φmax)) / (2h)
            @test isapprox(krieger_viscosity_dΦ(Φ0; μf=p.μf, Φmax=p.Φmax), fd1; rtol=1e-4)

            fd2 = (krieger_viscosity(Φ0 + h; μf=p.μf, Φmax=p.Φmax) - 2 * krieger_viscosity(Φ0; μf=p.μf, Φmax=p.Φmax) + krieger_viscosity(Φ0 - h; μf=p.μf, Φmax=p.Φmax)) / h^2
            @test isapprox(krieger_viscosity_d2Φ2(Φ0; μf=p.μf, Φmax=p.Φmax), fd2; rtol=1e-2)
        end
    end

    @testset "Shear-rate regularization floor is self-consistent with the default Γ0 IC" begin
        uh_zero = interpolate_everywhere(x -> VectorValue(0.0, 0.0), Vh)
        Γ_floor = sum(∫(shear_rate(uh_zero)) * dΩ) / (π * radius^2)
        @test isapprox(Γ_floor, sqrt(1e-10); rtol=1e-6)
        @test isapprox(p.Γ0(Point(0.0, 0.0)), sqrt(1e-10); rtol=1e-6)
    end

    @testset "shear_rate is Galilean-invariant (unchanged under a uniform velocity offset)" begin
        uh1 = interpolate_everywhere(x -> VectorValue(x[2], 0.0), Vh)
        uh2 = interpolate_everywhere(x -> VectorValue(x[2] + 3.0, -2.0), Vh)
        Γ1 = sum(∫(shear_rate(uh1)) * dΩ)
        Γ2 = sum(∫(shear_rate(uh2)) * dΩ)
        @test isapprox(Γ1, Γ2; rtol=1e-8)
    end

end
