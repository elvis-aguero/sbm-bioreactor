# Surviving container/host restarts: `-C generic`

Not enabled anywhere in this repo by default — this is a note for anyone hitting
the same problem, to opt into locally or in their own CI.

## The problem

By default, Julia precompiles packages ("pkgimages") with native code generation
targeting the exact CPU features detected on the build machine (`-C native`, the
default). Julia caches these compiled artifacts to disk so subsequent `using X`
calls don't have to recompile from scratch.

In an ephemeral/cloud dev environment, a container restart can land the next
process on a *different physical host* within the same fleet. If that host's CPU
lacks a feature the cached pkgimage was compiled to require (e.g. AVX-512 vs.
AVX2), Julia's load-time compatibility check rejects the cached artifact and
silently recompiles from scratch — even though the depot/filesystem itself
persisted across the restart. For a dependency stack like Gridap.jl + Plots.jl,
that recompile costs 20+ minutes, and it can recur on every restart.

Confirmed directly on this host (`Sys.CPU_NAME` = `cascadelake`): disassembling a
trivial function compiled under the default target showed 28 uses of `ymm`
(AVX2, 256-bit) registers; the same function compiled with `-C generic` used 0
`ymm`/`zmm` registers and only baseline `xmm` (SSE2) instructions — i.e. code
with no host-specific feature requirements, portable across any x86_64 host.

## The fix

Launch Julia with `-C generic` (equivalently `--cpu-target=generic`) for both
precompilation and execution:

```sh
julia -C generic --project=. your_script.jl
```

This makes `Base.compilecache_path` hash a `"generic"` target string into the
cache path (a separate cache slot from any existing native-target cache) and
compiles genuinely portable code, so the resulting pkgimage cache survives a
restart onto a different host in the same architecture family.

Note: setting the `JULIA_CPU_TARGET=generic` *environment variable* alone,
without the `-C` flag, does **not** change the current process's own JIT target
(verified: `Base.JLOptions().cpu_target` stayed `"native"` with only the env var
set). The env var is consulted by `Base.compilecache_path`/`Pkg`'s subprocess
spawning for building *other* packages' caches, but the process you actually
run needs the `-C generic` flag itself.

## Tradeoff

Generic/portable code forgoes this host's newer vector instructions (AVX2/
AVX-512), so hot numeric loops run somewhat slower than a native build. For a
one-shot illustrative render (or any workload where recompiling from scratch is
the real cost), that tradeoff is clearly worth it. Not applied as a project-wide
default here — if you want it in CI or your own machine, set it explicitly per
the command above.
