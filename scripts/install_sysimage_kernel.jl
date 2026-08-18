using IJulia
using Libdl

const ROOT = normpath(joinpath(@__DIR__, ".."))
const NOTEBOOK_PROJECT = joinpath(ROOT, "notebooks")
const ACTIVE_PROJECT = isdir(NOTEBOOK_PROJECT) ? NOTEBOOK_PROJECT : ROOT
const SYSIMAGE = joinpath(ROOT, "artifacts", "SBM_Bioreactor_sysimage.$(Libdl.dlext)")

if !isfile(SYSIMAGE)
    error("Sysimage not found at $SYSIMAGE. Build it first with `julia --project=. scripts/build_sysimage.jl`.")
end

installkernel(
    "Julia SBM Sysimage";
    env = Dict(),
    julia = Base.julia_cmd(),
    specname = "julia-sbm-sysimage",
    displayname = "Julia SBM Sysimage",
    argv = [
        Base.julia_cmd().exec[1],
        "--project=$ACTIVE_PROJECT",
        "-J$SYSIMAGE",
        "-i",
        "--color=yes",
        "--startup-file=yes",
        "--history-file=yes",
        joinpath(dirname(pathof(IJulia)), "kernel.jl"),
        "{connection_file}",
    ],
)

println("Installed kernel: Julia SBM Sysimage")
println("Sysimage: $SYSIMAGE")
