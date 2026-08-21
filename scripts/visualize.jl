using Gridap
using Plots
using SBM_Bioreactor

function mapped_grid_lines(map_fn, radius; nx=12, ny=12, samples=200)
    xs = range(-radius, radius; length=samples)
    ys = range(-radius, radius; length=samples)
    xlines = Tuple{Vector{Float64}, Vector{Float64}}[]
    ylines = Tuple{Vector{Float64}, Vector{Float64}}[]

    for x0 in range(-radius, radius; length=nx + 1)
        pts = [map_fn(Point(x0, y)) for y in ys]
        push!(xlines, ([p[1] for p in pts], [p[2] for p in pts]))
    end
    for y0 in range(-radius, radius; length=ny + 1)
        pts = [map_fn(Point(x, y0)) for x in xs]
        push!(ylines, ([p[1] for p in pts], [p[2] for p in pts]))
    end
    return xlines, ylines
end

function plot_harv_mesh(case; title="Mapped HARV Tutorial Mesh")
    xlines, ylines = mapped_grid_lines(
        case.metadata.map,
        case.metadata.radius;
        nx=case.metadata.partition[1],
        ny=case.metadata.partition[2],
    )
    plt = plot(legend=false, aspect_ratio=:equal, title=title, xlabel="x [m]", ylabel="y [m]")
    for (xs, ys) in xlines
        plot!(plt, xs, ys, color=:gray50, linewidth=1)
    end
    for (xs, ys) in ylines
        plot!(plt, xs, ys, color=:gray50, linewidth=1)
    end
    return plt
end

function sample_scalar_field(field; radius, n=121)
    xs = range(-radius, radius; length=n)
    ys = range(-radius, radius; length=n)
    values = Matrix{Float64}(undef, length(ys), length(xs))

    # field(Point(x,y)) alone calls evaluate(f,x) = evaluate!(return_cache(f,x),f,x),
    # and return_cache for a CellField/point rebuilds a KDTree over the whole mesh
    # from scratch (see Gridap's CellData/Interpolation.jl) -- looping that call
    # n^2 times rebuilds the same search structure n^2 times. Build the cache once
    # from the first in-mesh point and reuse it for every subsequent point instead;
    # this is the dominant cost in per-frame rendering, especially at video scale.
    cache = nothing
    for (j, y) in enumerate(ys), (i, x) in enumerate(xs)
        if x^2 + y^2 <= radius^2 + 1e-12
            pt = Point(x, y)
            # The square-to-disk mesh mapping is only approximately circular, so
            # a point that passes the disk-radius test can still land just
            # outside the mapped mesh near the boundary; treat those as NaN too.
            values[j, i] = try
                if cache === nothing
                    cache = Gridap.CellData.return_cache(field, pt)
                end
                Gridap.CellData.evaluate!(cache, field, pt)
            catch err
                err isa AssertionError ? NaN : rethrow()
            end
        else
            values[j, i] = NaN
        end
    end
    return xs, ys, values
end

function plot_initial_conditions(case; n=121)
    xs, ys, phi0 = sample_scalar_field(case.params.Φ0; radius=case.metadata.radius, n=n)
    _, _, c0 = sample_scalar_field(case.params.C0; radius=case.metadata.radius, n=n)

    plt_phi0 = heatmap(xs, ys, phi0, aspect_ratio=:equal, colorbar_title="Φ", title="Initial Cell Volume Fraction")
    plt_c0 = heatmap(xs, ys, c0, aspect_ratio=:equal, colorbar_title="C", title="Initial Nutrient Concentration")
    return plot(plt_phi0, plt_c0, layout=(1, 2), size=(1000, 400))
end

function plot_scalar_snapshot(field; radius, n=121, title="Scalar Field", colorbar_title="value")
    xs, ys, values = sample_scalar_field(x -> field(Point(x[1], x[2])); radius=radius, n=n)
    return heatmap(xs, ys, values, aspect_ratio=:equal, colorbar_title=colorbar_title, title=title)
end

function plot_scalar_history_snapshots(history, times; radius, n=121, nsnaps=3, colorbar_title="value", label="field")
    snap_indices = unique(round.(Int, range(1, length(history); length=min(length(history), nsnaps))))
    plots = Plots.Plot[]
    for idx in snap_indices
        push!(
            plots,
            plot_scalar_snapshot(
                history[idx];
                radius=radius,
                n=n,
                title="$(label) at t = $(round(times[idx], digits=2)) s",
                colorbar_title=colorbar_title,
            ),
        )
    end
    return plot(plots..., layout=(1, length(plots)), size=(350 * length(plots), 350))
end

function animate_scalar_history(history, times; radius, output_path, n=121, fps=4, colorbar_title="value", label="field")
    anim = @animate for (idx, field) in enumerate(history)
        plt = plot_scalar_snapshot(
            field;
            radius=radius,
            n=n,
            title="$(label)(t), t = $(round(times[idx], digits=2)) s",
            colorbar_title=colorbar_title,
        )
        display(plt)
    end

    if endswith(lowercase(output_path), ".gif")
        gif(anim, output_path, fps=fps)
    elseif endswith(lowercase(output_path), ".mp4")
        mp4(anim, output_path, fps=fps)
    else
        error("Unsupported animation extension for $output_path. Use .gif or .mp4.")
    end
    return output_path
end

"""
    interpolate_history(history, times, X; nframes)

Linearly blend each real solved snapshot's free-dof vector into `nframes`
evenly-spaced-in-time frames, for smooth video playback without re-solving more
timesteps. Valid for Lagrange nodal values: blending two snapshots' free-dof
vectors is itself a valid (if unphysical between exact solves) intermediate state,
good enough for a qualitative slide video.
"""
function interpolate_history(history, times, X; nframes)
    n = length(history)
    raw = [copy(get_free_dof_values(h)) for h in history]
    out_times = collect(range(times[1], times[end]; length=nframes))
    out_states = Vector{Any}(undef, nframes)
    for (k, t) in enumerate(out_times)
        i = clamp(searchsortedlast(times, t), 1, n - 1)
        i2 = i + 1
        α = (times[i2] > times[i]) ? (t - times[i]) / (times[i2] - times[i]) : 0.0
        α = clamp(α, 0.0, 1.0)
        vec = (1 - α) .* raw[i] .+ α .* raw[i2]
        out_states[k] = FEFunction(X, vec)
    end
    return out_states, out_times
end

vector_magnitude(field) = x -> sqrt(field(x)[1]^2 + field(x)[2]^2)

"""
    plot_bare_scalar_snapshot(field; radius, n=121)

A heatmap with no title, colorbar, axes, or ticks -- for slide videos where
Slidev's own caption carries any labeling, not the video itself.
"""
function plot_bare_scalar_snapshot(field; radius, n=121)
    xs, ys, values = sample_scalar_field(x -> field(Point(x[1], x[2])); radius=radius, n=n)
    return heatmap(
        xs, ys, values;
        aspect_ratio=:equal, colorbar=false, title="", legend=false,
        axis=false, ticks=false, framestyle=:none,
    )
end

function animate_bare_scalar(fields; radius, output_path, n=121, fps=30)
    anim = @animate for field in fields
        display(plot_bare_scalar_snapshot(field; radius=radius, n=n))
    end

    if endswith(lowercase(output_path), ".mp4")
        mp4(anim, output_path, fps=fps)
    elseif endswith(lowercase(output_path), ".gif")
        gif(anim, output_path, fps=fps)
    else
        error("Unsupported animation extension for $output_path. Use .gif or .mp4.")
    end
    return output_path
end

function demo_harv_visualization(; partition=(12, 12), dt=0.2, total_time=1.0, output_dir="notebooks/artifacts")
    case = build_harv_2d_case(partition=partition, dt=dt, total_time=total_time)
    result = run_bioreactor_simulation(
        case.X,
        case.Y,
        case.dΩ,
        case.metadata.dt,
        case.params,
        case.metadata.nsteps;
        collect_history=true,
        write_vtk_interval=0,
        output_prefix=joinpath(output_dir, "harv_demo"),
    )

    mkpath(output_dir)
    phi_history = [state[3] for state in result.history]

    return (
        case=case,
        result=result,
        mesh_plot=plot_harv_mesh(case),
        initial_plot=plot_initial_conditions(case),
        snapshot_plot=plot_scalar_history_snapshots(
            phi_history,
            result.times;
            radius=case.metadata.radius,
            colorbar_title="Φ",
            label="Φ",
        ),
    )
end
