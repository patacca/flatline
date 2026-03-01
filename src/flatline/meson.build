py.install_sources(
  '__init__.py',
  '_bridge.py',
  '_errors.py',
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
      nanobind_available = true
    endif
  endif

  if native_bridge_opt.enabled() and not nanobind_available
    error('native_bridge=enabled but nanobind is unavailable from ' + py.full_path())
  endif
endif

if nanobind_available
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
    install: true,
    subdir: 'flatline',
  )
endif
