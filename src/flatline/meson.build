py.install_sources(
  '__init__.py',
  '_artifacts.py',
  '_bridge.py',
  '_compliance.py',
  '_errors.py',
  '_footprint.py',
  '_release.py',
  '_models.py',
  '_runtime_data.py',
  '_session.py',
  '_version.py',
  subdir: 'flatline',
)

native_bridge_opt = get_option('native_bridge')
nanobind_available = false
nanobind_include_dir = ''
nanobind_source_dir = ''
nanobind_robin_map_include_dir = ''

if not native_bridge_opt.disabled()
  nanobind_probe = run_command(
    py,
    '-c',
    'import pathlib; import nanobind; root = pathlib.Path(nanobind.__file__).resolve().parent; print(nanobind.include_dir()); print(nanobind.source_dir()); print(root / "ext" / "robin_map" / "include")',
    check: false,
  )
  if nanobind_probe.returncode() == 0
    nanobind_lines = nanobind_probe.stdout().strip().split('\n')
    if nanobind_lines.length() == 3
      nanobind_include_dir = nanobind_lines[0]
      nanobind_source_dir = nanobind_lines[1]
      nanobind_robin_map_include_dir = nanobind_lines[2]

      # meson-python editable rebuilds run outside pip's build-isolation temp dirs.
      # Stage nanobind source + headers into the Meson build tree so paths remain valid.
      nanobind_stage_root = meson.current_build_dir() / 'nanobind_staged'
      nanobind_stage = run_command(
        py,
        '-c',
        'import pathlib; import shutil; import sys; include_dir = pathlib.Path(sys.argv[1]); source_dir = pathlib.Path(sys.argv[2]); robin_dir = pathlib.Path(sys.argv[3]); stage_root = pathlib.Path(sys.argv[4]); stage_root.mkdir(parents=True, exist_ok=True); shutil.copytree(include_dir, stage_root / "include", dirs_exist_ok=True); shutil.copytree(source_dir, stage_root / "src", dirs_exist_ok=True); shutil.copytree(robin_dir, stage_root / "robin_map_include", dirs_exist_ok=True)',
        nanobind_include_dir,
        nanobind_source_dir,
        nanobind_robin_map_include_dir,
        nanobind_stage_root,
        check: false,
      )
      if nanobind_stage.returncode() == 0
        nanobind_include_dir = nanobind_stage_root / 'include'
        nanobind_source_dir = nanobind_stage_root / 'src'
        nanobind_robin_map_include_dir = nanobind_stage_root / 'robin_map_include'
        nanobind_available = true
      endif
    endif
  endif

  if native_bridge_opt.enabled() and not nanobind_available
    error('native_bridge=enabled but nanobind is unavailable from ' + py.full_path())
  endif
endif

if nanobind_available
  # --- Ghidra decompiler static library ---
  # Source files derived from upstream Makefile LIBDECOMP target:
  #   CORE + DECCORE + SLEIGH + selected EXTRA (libdecomp, sleigh_arch, inject_sleigh).
  # Excludes: Ghidra Java bridge (*_ghidra.cc), BFD, console, XML arch, SLEIGH compiler,
  #   tests, and optional extras (rulecompile, unify, analyzesigs, codedata).

  ghidra_src = '../../third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp'

  ghidra_sources = [
    # CORE
    ghidra_src / 'xml.cc',
    ghidra_src / 'marshal.cc',
    ghidra_src / 'space.cc',
    ghidra_src / 'float.cc',
    ghidra_src / 'address.cc',
    ghidra_src / 'pcoderaw.cc',
    ghidra_src / 'translate.cc',
    ghidra_src / 'opcodes.cc',
    ghidra_src / 'globalcontext.cc',
    # DECCORE
    ghidra_src / 'capability.cc',
    ghidra_src / 'architecture.cc',
    ghidra_src / 'options.cc',
    ghidra_src / 'graph.cc',
    ghidra_src / 'cover.cc',
    ghidra_src / 'block.cc',
    ghidra_src / 'cast.cc',
    ghidra_src / 'typeop.cc',
    ghidra_src / 'database.cc',
    ghidra_src / 'cpool.cc',
    ghidra_src / 'comment.cc',
    ghidra_src / 'stringmanage.cc',
    ghidra_src / 'modelrules.cc',
    ghidra_src / 'fspec.cc',
    ghidra_src / 'action.cc',
    ghidra_src / 'loadimage.cc',
    ghidra_src / 'grammar.cc',
    ghidra_src / 'varnode.cc',
    ghidra_src / 'op.cc',
    ghidra_src / 'type.cc',
    ghidra_src / 'variable.cc',
    ghidra_src / 'varmap.cc',
    ghidra_src / 'jumptable.cc',
    ghidra_src / 'emulate.cc',
    ghidra_src / 'emulateutil.cc',
    ghidra_src / 'flow.cc',
    ghidra_src / 'userop.cc',
    ghidra_src / 'expression.cc',
    ghidra_src / 'multiprecision.cc',
    ghidra_src / 'funcdata.cc',
    ghidra_src / 'funcdata_block.cc',
    ghidra_src / 'funcdata_op.cc',
    ghidra_src / 'funcdata_varnode.cc',
    ghidra_src / 'unionresolve.cc',
    ghidra_src / 'pcodeinject.cc',
    ghidra_src / 'heritage.cc',
    ghidra_src / 'prefersplit.cc',
    ghidra_src / 'rangeutil.cc',
    ghidra_src / 'ruleaction.cc',
    ghidra_src / 'subflow.cc',
    ghidra_src / 'blockaction.cc',
    ghidra_src / 'merge.cc',
    ghidra_src / 'double.cc',
    ghidra_src / 'transform.cc',
    ghidra_src / 'constseq.cc',
    ghidra_src / 'coreaction.cc',
    ghidra_src / 'condexe.cc',
    ghidra_src / 'override.cc',
    ghidra_src / 'dynamic.cc',
    ghidra_src / 'crc32.cc',
    ghidra_src / 'prettyprint.cc',
    ghidra_src / 'printlanguage.cc',
    ghidra_src / 'printc.cc',
    ghidra_src / 'printjava.cc',
    ghidra_src / 'memstate.cc',
    ghidra_src / 'opbehavior.cc',
    ghidra_src / 'paramid.cc',
    ghidra_src / 'signature.cc',
    # SLEIGH
    ghidra_src / 'sleigh.cc',
    ghidra_src / 'pcodeparse.cc',
    ghidra_src / 'pcodecompile.cc',
    ghidra_src / 'sleighbase.cc',
    ghidra_src / 'slghsymbol.cc',
    ghidra_src / 'slghpatexpress.cc',
    ghidra_src / 'slghpattern.cc',
    ghidra_src / 'semantics.cc',
    ghidra_src / 'context.cc',
    ghidra_src / 'slaformat.cc',
    ghidra_src / 'compression.cc',
    ghidra_src / 'filemanage.cc',
    # EXTRA (selected)
    ghidra_src / 'libdecomp.cc',
    ghidra_src / 'sleigh_arch.cc',
    ghidra_src / 'inject_sleigh.cc',
  ]

  ghidra_inc = include_directories(ghidra_src)

  zlib_dep = dependency('zlib')

  ghidra_decompiler_lib = static_library(
    'ghidra_decompiler',
    ghidra_sources,
    include_directories: ghidra_inc,
    dependencies: zlib_dep,
    cpp_args: ['-w'],
  )

  # --- nanobind extension module ---
  py.extension_module(
    '_flatline_native',
    [
      '_flatline_native.cpp',
      nanobind_source_dir / 'nb_combined.cpp',
    ],
    cpp_args: [
      '-fvisibility=hidden',
      '-fno-strict-aliasing',
      '-DNB_COMPACT_ASSERTIONS',
      '-I' + nanobind_include_dir,
      '-I' + nanobind_source_dir,
      '-I' + nanobind_robin_map_include_dir,
    ],
    include_directories: ghidra_inc,
    link_with: ghidra_decompiler_lib,
    dependencies: zlib_dep,
    install: true,
    subdir: 'flatline',
  )
endif
