py.install_sources(
  '__init__.py',
  '_bridge.py',
  '_bridge_payloads.py',
  '_errors.py',
  '_models.py',
  '_models_enriched.py',
  '_models_request.py',
  '_models_types.py',
  '_runtime_data.py',
  '_session.py',
  '_version.py',
  '_windows.py',
  subdir: 'flatline',
)

cpp = meson.get_compiler('cpp')
cpp_argument_syntax = cpp.get_argument_syntax()

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
  ghidra_cpp_args = []
  native_bridge_cpp_args = [
    '-DNB_COMPACT_ASSERTIONS',
  ]
  if cpp_argument_syntax == 'msvc'
    ghidra_cpp_args += ['/w']
  else
    ghidra_cpp_args += ['-w']
    native_bridge_cpp_args += [
      '-fvisibility=hidden',
      '-fno-strict-aliasing',
    ]
  endif
  if host_machine.system() == 'windows'
    ghidra_cpp_args += ['-D_WINDOWS', '-DWINDOWS']
  endif
  nanobind_inc = include_directories(
    'nanobind_staged/include',
    'nanobind_staged/src',
    'nanobind_staged/robin_map_include',
  )

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

  zlib_dep = dependency('zlib', required: false)

  if not zlib_dep.found() and host_machine.system() == 'darwin'
    brew = find_program('brew', required: false)
    if brew.found()
      brew_zlib_prefix = run_command(brew, '--prefix', 'zlib', check: false)
      if brew_zlib_prefix.returncode() == 0
        zlib_prefix = brew_zlib_prefix.stdout().strip()
        if zlib_prefix != ''
          zlib_lib = cpp.find_library('z', dirs: [zlib_prefix + '/lib'], required: false)
          if zlib_lib.found()
            zlib_dep = declare_dependency(
              dependencies: [zlib_lib],
              include_directories: include_directories(zlib_prefix + '/include'),
            )
          endif
        endif
      endif
    endif
  endif

  if not zlib_dep.found() and host_machine.system() == 'windows'
    vcpkg_root_probe = run_command(
      py, '-c',
      'import os, shutil; root = os.environ.get("VCPKG_INSTALLATION_ROOT", ""); exe = shutil.which("vcpkg") if not root else None; print(root or (os.path.dirname(os.path.realpath(exe)) if exe else ""))',
      check: false,
    )
    if vcpkg_root_probe.returncode() == 0
      vcpkg_root = vcpkg_root_probe.stdout().strip()
      if vcpkg_root != ''
        vcpkg_prefix = vcpkg_root + '/installed/x64-windows'
        zlib_lib = cpp.find_library('zlib', dirs: [vcpkg_prefix + '/lib'], required: false)
        if zlib_lib.found()
          zlib_dep = declare_dependency(
            dependencies: [zlib_lib],
            include_directories: include_directories(vcpkg_prefix + '/include'),
          )
        endif
      endif
    endif
  endif

  if not zlib_dep.found()
    error('zlib not found. Install the platform zlib development package; on macOS, `brew install zlib`; on Windows, `vcpkg install zlib:x64-windows` with VCPKG_INSTALLATION_ROOT set.')
  endif

  ghidra_decompiler_lib = static_library(
    'ghidra_decompiler',
    ghidra_sources,
    include_directories: ghidra_inc,
    dependencies: zlib_dep,
    cpp_args: ghidra_cpp_args,
  )

  # --- nanobind extension module ---
  py.extension_module(
    '_flatline_native',
    [
      '_flatline_native.cpp',
      '_flatline_native_memory.cpp',
      '_flatline_native_pcode.cpp',
      '_flatline_native_session.cpp',
      '_flatline_native_shared.cpp',
      nanobind_source_dir / 'nb_combined.cpp',
    ],
    cpp_args: native_bridge_cpp_args,
    include_directories: [ghidra_inc, nanobind_inc],
    link_whole: ghidra_decompiler_lib,
    dependencies: zlib_dep,
    install: true,
    subdir: 'flatline',
  )
endif
