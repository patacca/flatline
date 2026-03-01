py.install_sources(
  '__init__.py',
  '_bridge.py',
  '_errors.py',
  '_models.py',
  '_session.py',
  '_version.py',
  subdir: 'flatline',
)

native_bridge_opt = get_option('native_bridge')
nanobind_dep = dependency('nanobind', required: native_bridge_opt)

if nanobind_dep.found()
  py.extension_module(
    '_flatline_native',
    '_flatline_native.cpp',
    dependencies: [nanobind_dep],
    cpp_args: ['-std=c++17'],
    install: true,
    subdir: 'flatline',
  )
endif
