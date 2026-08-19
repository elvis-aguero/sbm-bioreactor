# scripts/daemon_serve.jl
#
# Starts a persistent Julia daemon (DaemonMode.jl) with this project's environment
# active. Gridap's AD-based residual assembly for the monolithic 5-field solver is
# expensive to JIT-compile the first time (tens of minutes) -- this daemon pays that
# cost exactly once. Every later `julia scripts/daemon_client.jl <script>.jl` call runs
# against this already-warm process instead of starting a fresh `julia`, and reuses its
# compiled code (each script still runs in its own fresh module, so variables don't leak
# between calls -- see DaemonMode's docs).
#
# Usage (start once, leave it running):
#   julia --project=. scripts/daemon_serve.jl &
#
# Then, instead of `julia --project=. some_script.jl`, run:
#   julia scripts/daemon_client.jl some_script.jl
#
# Stop it with: julia scripts/daemon_client.jl --stop   (or just kill the process)
using DaemonMode

serve()
