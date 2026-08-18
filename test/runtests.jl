# test/runtests.jl
#
# Main test runner for the SBM_Bioreactor package. Executes various sub-testsets to
# verify physical components, solver stability, and numerical convergence.
using Test
using SBM_Bioreactor

@testset "Module Loading" begin
    # Verify the package exports and module environment load correctly.
    @test true
end

# Each included file contains dedicated @testset blocks for specific components.
include("test_navier_stokes.jl")
include("test_rheology.jl")
include("test_migration.jl")
include("test_solver.jl")
include("test_mms.jl")
include("test_mms_unsteady.jl")
include("test_examples.jl")
