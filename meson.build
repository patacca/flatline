project(
  'flatline',
  'cpp',
  version: '0.1.1.dev1',
  license: 'Apache-2.0',
  meson_version: '>= 1.6',
  default_options: ['cpp_std=c++20', 'buildtype=release'],
)

py = import('python').find_installation(pure: false)

subdir('src/flatline')

fs = import('fs')
if fs.exists('tools/prune_dist.py')
  meson.add_dist_script(py, files('tools/prune_dist.py'))
endif
