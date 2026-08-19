# scripts/daemon_client.jl
#
# Lightweight client for scripts/daemon_serve.jl. Forwards the target script (and any
# extra arguments) to the already-running daemon over a local socket, instead of
# starting a fresh `julia` process that would have to recompile everything.
#
# Usage:
#   julia scripts/daemon_client.jl <script.jl> [args...]
using DaemonMode

runargs()
