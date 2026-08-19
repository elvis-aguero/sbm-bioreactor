# test/runtests.jl
#
# Main test runner for the SBM_Bioreactor package. Executes various sub-testsets to
# verify physical components, solver stability, and numerical convergence.
using Test
using SBM_Bioreactor

const T_START = time()

@testset "Module Loading" begin
    # Verify the package exports and module environment load correctly.
    @test true
end

# Each included file contains dedicated @testset blocks for specific components.
#
# stdout is block-buffered (not line-buffered) when it isn't a TTY, which is always
# the case under GitHub Actions -- without an explicit flush after each file, CI log
# output (and any in-progress log fetch) shows nothing until the whole test process
# exits, making a hang in any one file indistinguishable from a hang anywhere else.
const TEST_FILES = [
    "test_navier_stokes.jl",
    "test_rheology.jl",
    "test_migration.jl",
    "test_solver.jl",
    "test_analytic_jacobian.jl",
    "test_mms.jl",
    "test_mms_unsteady.jl",
    "test_examples.jl",
]

for file in TEST_FILES
    println("=== [", round(time() - T_START, digits=1), "s] starting $file ===")
    flush(stdout)
    include(file)
    println("=== [", round(time() - T_START, digits=1), "s] finished $file ===")
    flush(stdout)
end
