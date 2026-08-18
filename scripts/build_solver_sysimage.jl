using PackageCompiler
using Libdl
using Pkg

const ROOT = normpath(joinpath(@__DIR__, ".."))
const OUTPUT = joinpath(ROOT, "artifacts", "SBM_solver_sysimage.$(Libdl.dlext)")

mkpath(dirname(OUTPUT))

function build_solver_sysimage()
    ctx = PackageCompiler.create_pkg_context(ROOT)
    PackageCompiler.check_packages_in_project(ctx, ["SBM_Bioreactor"])
    Pkg.instantiate(ctx; verbose=true, allow_autoprecomp=false)

    base_sysimage = unsafe_string(Base.JLOptions().image_file)

    object_file = tempname() * "-o.a"
    try
        PackageCompiler.create_sysimg_object_file(
            object_file,
            ["SBM_Bioreactor"],
            Set{Base.PkgId}();
            project=ROOT,
            base_sysimage=base_sysimage,
            precompile_execution_file=String[],
            precompile_statements_file=String[],
            cpu_target=PackageCompiler.NATIVE_CPU_TARGET,
            script=nothing,
            sysimage_build_args=``,
            extra_precompiles="",
            incremental=true,
            import_into_main=true,
        )

        PackageCompiler.create_sysimg_from_object_file(
            [object_file],
            OUTPUT;
            version=nothing,
            compat_level="major",
            soname=nothing,
        )
    finally
        rm(object_file; force=true)
    end

    println(OUTPUT)
end

build_solver_sysimage()
