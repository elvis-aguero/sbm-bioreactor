using Test
using Gridap
using SBM_Bioreactor

@testset "HARV Example API" begin
    @test isdefined(SBM_Bioreactor, :build_harv_2d_case)
    @test isdefined(SBM_Bioreactor, :run_bioreactor_simulation)

    case = build_harv_2d_case(partition=(2, 2), dt=0.25, total_time=0.5)

    @test num_fields(case.X) == 5
    @test num_fields(case.Y) == 5
    @test case.metadata.nsteps == 2
    @test case.metadata.partition == (2, 2)
    @test case.metadata.dt == 0.25
    @test case.params.Φ0(Point(0.0, 0.03)) ≈ 0.1
    @test case.params.Φ0(Point(0.0, 0.0)) ≈ 0.0
    @test case.params.Γ0(Point(0.0, 0.0)) > 0.0

    blocked_case = build_harv_2d_case(partition=(2, 2), dt=0.25, total_time=0.5, blocked=true)
    blocked_state = interpolate_everywhere(
        [blocked_case.params.u0, blocked_case.params.p0, blocked_case.params.Φ0, blocked_case.params.C0, blocked_case.params.Γ0],
        blocked_case.X,
    )
    @test blocked_case.metadata.blocked == true
    @test num_fields(blocked_case.X) == 5
    @test occursin("BlockVector", string(typeof(get_free_dof_values(blocked_state))))

    result = run_bioreactor_simulation(
        case.X,
        case.Y,
        case.dΩ,
        case.metadata.dt,
        case.params,
        0;
        write_vtk_interval=0,
        collect_history=true,
    )

    @test length(result.history) == 1
    @test result.times == [0.0]
    @test length(result.final_state) == 5
    @test !haskey(result, :profile)

    result_no_history = run_bioreactor_simulation(
        case.X,
        case.Y,
        case.dΩ,
        case.metadata.dt,
        case.params,
        0;
        write_vtk_interval=0,
        collect_history=false,
    )

    @test num_fields(result_no_history) == 5

    profiled = run_bioreactor_simulation(
        case.X,
        case.Y,
        case.dΩ,
        case.metadata.dt,
        case.params,
        0;
        write_vtk_interval=0,
        collect_history=true,
        profile_steps=true,
    )

    @test haskey(profiled, :profile)
    @test profiled.profile.initial_setup_time >= 0.0
    @test isempty(profiled.profile.steps)

    history_case = build_harv_2d_case(partition=(1, 1), dt=0.05, total_time=0.10, degree=2, blocked=true)
    history_params = merge(
        history_case.params,
        (
            use_explicit_jacobian = true,
            enable_particle_flux = false,
            freeze_viscosity = true,
            include_convection = false,
            enable_growth_source = false,
            enable_nutrient_reaction = false,
        ),
    )
    history_result = run_bioreactor_simulation(
        history_case.X,
        history_case.Y,
        history_case.dΩ,
        history_case.metadata.dt,
        history_params,
        history_case.metadata.nsteps;
        collect_history=true,
        write_vtk_interval=0,
        nonlinear_show_trace=false,
        max_order=1,
        blocked_linear_solver=true,
        blocked_outer_solver=:gmres,
        transport_block_solver=:lu,
    )

    @test length(history_result.history) == history_case.metadata.nsteps + 1
    @test history_result.history[2] !== history_result.history[3]
end

if get(ENV, "SBM_RUN_PLOTS_TESTS", "0") == "1"
    @testset "Visualization Helper Loading" begin
        plots_available = false
        try
            @eval using Plots
            plots_available = true
        catch
            plots_available = false
        end

        if plots_available
            include("../scripts/visualize.jl")
            case = build_harv_2d_case(partition=(2, 2), total_time=0.0)
            plt = plot_harv_mesh(case)
            @test plt isa Plots.Plot
        else
            @test_broken false
        end
    end
end
