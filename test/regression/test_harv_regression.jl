using Test
using JSON3
using SBM_Bioreactor

@testset "HARV Coarse Regression Scaffold" begin
    baseline = JSON3.read(read(joinpath(@__DIR__, "baselines", "harv_2d_coarse_summary.json"), String))

    @test haskey(baseline, :description) || haskey(baseline, "description")

    case = build_harv_2d_case(partition=(4, 4), dt=0.25, total_time=0.5)
    @test case.metadata.nsteps == 2

    # Full regression execution is intentionally deferred until a first approved baseline is generated.
    @test true
end
