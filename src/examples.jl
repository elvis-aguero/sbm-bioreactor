using Gridap

"""
    harv_square_to_disk(p; radius=0.05)

Map a point from the square reference box to a disk of the given radius.
"""
function harv_square_to_disk(p; radius=0.05)
    x, y = p[1], p[2]
    X = x / radius
    Y = y / radius
    x_new = X * sqrt(1.0 - Y^2 / 2.0)
    y_new = Y * sqrt(1.0 - X^2 / 2.0)
    return VectorValue(x_new * radius, y_new * radius)
end

"""
    build_harv_2d_case(; kwargs...)

Construct a tutorial-scale 2D HARV setup compatible with the current 5-field solver.
"""
function build_harv_2d_case(;
    radius=0.05,
    partition=(10, 10),
    degree=4,
    omega_rpm=7.5,
    dt=0.1,
    total_time=10.0,
    phi_cloud=0.1,
    phi_cutoff=0.02,
    phiavg=0.05,
)
    map_fn = x -> harv_square_to_disk(x; radius=radius)
    domain = (-radius, radius, -radius, radius)
    model = CartesianDiscreteModel(domain, partition, map=map_fn)

    reffe_u = ReferenceFE(lagrangian, VectorValue{2, Float64}, 2)
    reffe_p = ReferenceFE(lagrangian, Float64, 1)
    reffe_s = ReferenceFE(lagrangian, Float64, 1)

    ω = omega_rpm * 2π / 60.0
    u_wall(x) = VectorValue(ω * x[2], -ω * x[1])

    V = TestFESpace(model, reffe_u, conformity=:H1, dirichlet_tags="boundary")
    Q = TestFESpace(model, reffe_p, conformity=:H1, constraint=:zeromean)
    W = TestFESpace(model, reffe_s, conformity=:H1)
    Z = TestFESpace(model, reffe_s, conformity=:H1)
    G = TestFESpace(model, reffe_s, conformity=:H1)

    U = TrialFESpace(V, u_wall)
    P = TrialFESpace(Q)
    Φ_space = TrialFESpace(W)
    C_space = TrialFESpace(Z)
    Γ_space = TrialFESpace(G)

    Y = MultiFieldFESpace([V, Q, W, Z, G])
    X = MultiFieldFESpace([U, P, Φ_space, C_space, Γ_space])

    Ω = Triangulation(model)
    dΩ = Measure(Ω, degree)

    params = (
        μf = 0.5889,
        Φmax = 0.64,
        a = 5.0e-6,
        ρs = 1000.0,
        ρf = 1050.0,
        g = VectorValue(0.0, -9.81),
        Df = 5.4e-10,
        Φavg = phiavg,
        L = 0.01,
        u_wall = u_wall,
        kc = 1.0e-13,
        ke = 4.2e-6,
        d0 = 3.0e5,
        # Fluid starts at rest, not already spun up: u_wall only constrains the
        # boundary (Dirichlet) DOFs of the trial space regardless of what's passed
        # here, so this genuinely models "impulsively started rotating wall, fluid
        # initially at rest" (the classic spin-up problem) rather than skipping the
        # startup transient by initializing already at rigid rotation everywhere.
        u0 = x -> VectorValue(0.0, 0.0),
        p0 = x -> 0.0,
        Φ0 = x -> (x[2] > phi_cutoff ? phi_cloud : 0.0),
        C0 = x -> 5.5,
        Γ0 = x -> 1.0e-5,
    )

    metadata = (
        radius = radius,
        domain = domain,
        partition = partition,
        degree = degree,
        omega_rpm = omega_rpm,
        dt = dt,
        total_time = total_time,
        nsteps = Int(round(total_time / dt)),
        map = map_fn,
    )

    return (
        model = model,
        X = X,
        Y = Y,
        dΩ = dΩ,
        params = params,
        metadata = metadata,
    )
end
