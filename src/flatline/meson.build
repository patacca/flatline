py.install_sources(
  '__init__.py',
  '_errors.py',
  '_session.py',
  '_version.py',
  subdir: 'flatline',
)

py.install_sources(
  '_native_layout/__init__.py',
  subdir: 'flatline/_native_layout',
)

py.install_sources(
  'bridge/__init__.py',
  'bridge/_coercion_utils.py',
  'bridge/core.py',
  'bridge/payloads.py',
  subdir: 'flatline/bridge',
)

py.install_sources(
  'models/__init__.py',
  'models/enriched.py',
  'models/enums.py',
  'models/request.py',
  'models/types.py',
  'models/varnodes.py',
  subdir: 'flatline/models',
)

py.install_sources(
  'models/pcode_ops/__init__.py',
  'models/pcode_ops/_base.py',
  'models/pcode_ops/arithmetic.py',
  'models/pcode_ops/bitwise.py',
  'models/pcode_ops/boolean.py',
  'models/pcode_ops/branch.py',
  'models/pcode_ops/call.py',
  'models/pcode_ops/comparison.py',
  'models/pcode_ops/copy.py',
  'models/pcode_ops/dataflow.py',
  'models/pcode_ops/highlevel.py',
  'models/pcode_ops/memory.py',
  subdir: 'flatline/models/pcode_ops',
)

py.install_sources(
  'runtime/__init__.py',
  'runtime/discovery.py',
  'runtime/windows.py',
  subdir: 'flatline/runtime',
)

py.install_sources(
  'xray/__init__.py',
  'xray/__main__.py',
  'xray/_canvas.py',
  'xray/_cpg_overlay.py',
  'xray/_edge_routing.py',
  'xray/_edge_routing_legacy.py',
  'xray/_edge_slots.py',
  'xray/_graph_window.py',
  'xray/_inputs.py',
  'xray/_inspector.py',
  'xray/_layout.py',
  'xray/_theme.py',
  subdir: 'flatline/xray',
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

  # --- OGDF static library (layout backend) ---
  # Layered subset only; OptimalHierarchyLayout.cpp and
  # OptimalHierarchyClusterLayout.cpp are excluded because they depend on
  # COIN-OR. The cluster variant has a no-op stub so OGDF's vtables resolve.
  # config_autogen.h under native/ogdf/basic/internal/ is a hand-written,
  # cross-platform replacement for OGDF's CMake-generated header.
  ogdf_src = '../../third_party/ogdf/src/ogdf'
  ogdf_inc = include_directories(
    'native',
    '../../third_party/ogdf/include',
  )

  ogdf_section_cpp_args = []
  ogdf_section_link_args = []
  if cpp_argument_syntax != 'msvc'
    ogdf_section_cpp_args = ['-ffunction-sections', '-fdata-sections']
    if host_machine.system() == 'darwin'
      ogdf_section_link_args = ['-Wl,-dead_strip']
    else
      ogdf_section_link_args = ['-Wl,--gc-sections']
    endif
  else
    ogdf_section_cpp_args = ['/Gy']
    ogdf_section_link_args = ['/OPT:REF']
  endif

  ogdf_cpp_args = ogdf_section_cpp_args
  if cpp_argument_syntax == 'msvc'
    ogdf_cpp_args += ['/w']
  else
    ogdf_cpp_args += ['-w']
  endif

  ogdf_sources = [
    ogdf_src / 'basic/basic.cpp',
    ogdf_src / 'basic/CombinatorialEmbedding.cpp',
    ogdf_src / 'basic/Graph.cpp',
    ogdf_src / 'basic/GraphAttributes.cpp',
    ogdf_src / 'basic/GraphCopy.cpp',
    ogdf_src / 'basic/LayoutStandards.cpp',
    ogdf_src / 'basic/Logger.cpp',
    ogdf_src / 'basic/System.cpp',
    ogdf_src / 'basic/geometry.cpp',
    ogdf_src / 'basic/graphics.cpp',
    ogdf_src / 'basic/memory/PoolMemoryAllocator.cpp',
    ogdf_src / 'basic/simple_graph_alg.cpp',
    ogdf_src / 'cluster/ClusterGraph.cpp',
    ogdf_src / 'layered/BarycenterHeuristic.cpp',
    ogdf_src / 'layered/CrossingMinInterfaces.cpp',
    ogdf_src / 'layered/CrossingsMatrix.cpp',
    ogdf_src / 'layered/DfsAcyclicSubgraph.cpp',
    ogdf_src / 'layered/ExtendedNestingGraph.cpp',
    ogdf_src / 'layered/FastHierarchyLayout.cpp',
    ogdf_src / 'layered/LongestPathRanking.cpp',
    ogdf_src / 'layered/OptimalRanking.cpp',
    ogdf_src / 'layered/SplitHeuristic.cpp',
    ogdf_src / 'layered/SugiyamaLayout.cpp',
    ogdf_src / 'packing/TileToRowsCCPacker.cpp',
    'native/ogdf_optimal_hierarchy_cluster_stub.cpp',
  ]

  thread_dep = dependency('threads')

  ogdf_lib = static_library(
    'ogdf_lib',
    ogdf_sources,
    include_directories: ogdf_inc,
    dependencies: thread_dep,
    cpp_args: ogdf_cpp_args,
  )

  # --- libavoid static library (edge routing) ---
  # All 23 .cpp files from cola/libavoid/; zero external dependencies.
  libavoid_src = '../../third_party/libavoid_src/cola/libavoid'
  libavoid_inc = include_directories('../../third_party/libavoid_src/cola')

  libavoid_cpp_args = ogdf_section_cpp_args
  if cpp_argument_syntax != 'msvc'
    libavoid_cpp_args += ['-Wno-deprecated-declarations']
  endif

  libavoid_sources = [
    libavoid_src / 'actioninfo.cpp',
    libavoid_src / 'connectionpin.cpp',
    libavoid_src / 'connector.cpp',
    libavoid_src / 'connend.cpp',
    libavoid_src / 'geometry.cpp',
    libavoid_src / 'geomtypes.cpp',
    libavoid_src / 'graph.cpp',
    libavoid_src / 'hyperedge.cpp',
    libavoid_src / 'hyperedgeimprover.cpp',
    libavoid_src / 'hyperedgetree.cpp',
    libavoid_src / 'junction.cpp',
    libavoid_src / 'makepath.cpp',
    libavoid_src / 'mtst.cpp',
    libavoid_src / 'obstacle.cpp',
    libavoid_src / 'orthogonal.cpp',
    libavoid_src / 'router.cpp',
    libavoid_src / 'scanline.cpp',
    libavoid_src / 'shape.cpp',
    libavoid_src / 'timer.cpp',
    libavoid_src / 'vertices.cpp',
    libavoid_src / 'viscluster.cpp',
    libavoid_src / 'visibility.cpp',
    libavoid_src / 'vpsc.cpp',
  ]

  libavoid_lib = static_library(
    'libavoid_lib',
    libavoid_sources,
    include_directories: libavoid_inc,
    cpp_args: libavoid_cpp_args,
  )

  # --- nanobind extension module ---
  py.extension_module(
    '_flatline_native',
    [
      'native/module.cpp',
      'native/memory.cpp',
      'native/disasm.cpp',
      'native/pcode.cpp',
      'native/session.cpp',
      'native/shared.cpp',
      nanobind_source_dir / 'nb_combined.cpp',
    ],
    cpp_args: native_bridge_cpp_args,
    include_directories: [ghidra_inc, nanobind_inc, ogdf_inc, libavoid_inc],
    link_whole: [ghidra_decompiler_lib, ogdf_lib, libavoid_lib],
    dependencies: [zlib_dep, thread_dep],
    link_args: ogdf_section_link_args,
    install: true,
    subdir: 'flatline',
  )
endif
