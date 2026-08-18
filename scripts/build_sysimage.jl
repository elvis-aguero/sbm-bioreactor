using PackageCompiler
using Libdl

const ROOT = normpath(joinpath(@__DIR__, ".."))
const DEFAULT_PROJECT = joinpath(ROOT, "notebooks")
const ACTIVE_PROJECT = isdir(DEFAULT_PROJECT) ? DEFAULT_PROJECT : ROOT
const WORKLOAD = joinpath(ROOT, "scripts", "precompile_sysimage_workload.jl")
const OUTPUT = joinpath(ROOT, "artifacts", "SBM_Bioreactor_sysimage.$(Libdl.dlext)")

mkpath(dirname(OUTPUT))

create_sysimage(
    ["SBM_Bioreactor"];
    project = ACTIVE_PROJECT,
    sysimage_path = OUTPUT,
    precompile_execution_file = WORKLOAD,
    incremental = false,
    filter_stdlibs = true,
    include_transitive_dependencies = false,
)

println(OUTPUT)
