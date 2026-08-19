using Test
using Gridap
using SBM_Bioreactor

@testset "HARV Example API" begin
    case = build_harv_2d_case(partition=(2, 2), dt=0.25, total_time=0.5)

    @test num_fields(case.X) == 5
    @test num_fields(case.Y) == 5
    @test case.metadata.nsteps == 2
    @test case.params.Φ0(Point(0.0, 0.03)) ≈ 0.1
    @test case.params.Φ0(Point(0.0, 0.0)) ≈ 0.0
    @test case.params.Γ0(Point(0.0, 0.0)) > 0.0

    println("  [test_examples] starting run_bioreactor_simulation..."); flush(stdout)
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
    println("  [test_examples] run_bioreactor_simulation done."); flush(stdout)

    @test length(result.history) == 1
    @test result.times == [0.0]
    @test length(result.final_state) == 5
end

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
