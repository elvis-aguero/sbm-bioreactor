# scripts/daemon_serve.jl
#
# Starts a persistent Julia daemon (DaemonMode.jl) with this project's environment
# active, running under Revise.jl. Two distinct costs this addresses:
#
# 1. Package LOADING cost (~13s to load Gridap/SBM_Bioreactor's precompiled images into
#    a fresh process) -- avoided because this daemon loads them once and stays warm;
#    every `daemon_client.jl` call runs against the already-loaded process instead of
#    starting a fresh `julia`.
# 2. Package PRECOMPILATION cost (tens of minutes, whenever src/ actually changes) --
#    avoided for ordinary function-body edits because Revise is loaded *before*
#    SBM_Bioreactor ever gets `using`'d in this process. Revise patches the live,
#    already-loaded module in place when its source files change on disk, instead of
#    going through Pkg's full package-precompile pipeline. This is what actually matters
#    during active development, where src/ changes constantly and the formal
#    @compile_workload-based precompile cache never gets a chance to be reused.
#
# Caveat (inherent to Revise/any live-patching, not specific to this setup): redefining
# a `struct`'s fields (not just a function body) can't be hot-patched -- Julia doesn't
# support changing a type's layout in a running process. That needs a daemon restart.
# Ordinary function-body edits (the common case) don't.
#
# Usage (start once, leave it running):
#   julia --project=. scripts/daemon_serve.jl &
#
# Then, instead of `julia --project=. some_script.jl`, run:
#   julia scripts/daemon_client.jl some_script.jl
#
# Stop it with: julia scripts/daemon_client.jl --stop   (or just kill the process)
using Revise
using DaemonMode

serve()
