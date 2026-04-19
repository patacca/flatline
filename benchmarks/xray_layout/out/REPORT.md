---
generated_at: "2026-04-19T20:51:07.542218+00:00"
git_sha: "0a02fcd"
branch: "bench/xray-layout-comparison"
machine:
  cpu: "Intel(R) Core(TM) Ultra 5 225H"
  ram_gb: 30.83
  os: "Linux-6.19.8-arch1-1-x86_64-with-glibc2.43"
  python: "3.14.3"
benchmark_version: "0.0.0"
---

# xray Layout Library Benchmark Report

## Executive Summary

| Candidate | Tier | Binaries OK |
|---|---|---|
| libavoid | Deferred | 0/5 |
| hola | Tier 1 | 1/5 |
| ogdf | Deferred | 0/5 |
| domus | Tier 1 | 0/5 |
| wueortho | Deferred | 0/5 |
| ogdf_libavoid | Deferred | 0/5 |

## Results by Binary

### tiny_branch

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| hola | ok | 1.0 | 1625.0 | 184.6 | 0.0 | 105750.0 | 2.1 | 32.0 | 0.0 | 113.6 |
| libavoid | deferred | - | - | - | - | - | - | - | - | - |
| ogdf | deferred | - | - | - | - | - | - | - | - | - |
| domus | error | - | - | - | - | - | - | - | - | - |
| wueortho | deferred | - | - | - | - | - | - | - | - | - |
| ogdf_libavoid | deferred | - | - | - | - | - | - | - | - | - |

![tiny_branch grid](renders/tiny_branch__GRID.png)

### small_loop

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | deferred | - | - | - | - | - | - | - | - | - |
| hola | error | - | - | - | - | - | - | - | - | - |
| ogdf | deferred | - | - | - | - | - | - | - | - | - |
| domus | error | - | - | - | - | - | - | - | - | - |
| wueortho | deferred | - | - | - | - | - | - | - | - | - |
| ogdf_libavoid | deferred | - | - | - | - | - | - | - | - | - |

*Grid not available for small_loop*

### medium_switch

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | deferred | - | - | - | - | - | - | - | - | - |
| hola | error | - | - | - | - | - | - | - | - | - |
| ogdf | deferred | - | - | - | - | - | - | - | - | - |
| domus | error | - | - | - | - | - | - | - | - | - |
| wueortho | deferred | - | - | - | - | - | - | - | - | - |
| ogdf_libavoid | deferred | - | - | - | - | - | - | - | - | - |

*Grid not available for medium_switch*

### large_nested

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | deferred | - | - | - | - | - | - | - | - | - |
| hola | error | - | - | - | - | - | - | - | - | - |
| ogdf | deferred | - | - | - | - | - | - | - | - | - |
| domus | error | - | - | - | - | - | - | - | - | - |
| wueortho | deferred | - | - | - | - | - | - | - | - | - |
| ogdf_libavoid | deferred | - | - | - | - | - | - | - | - | - |

*Grid not available for large_nested*

### xlarge_state_machine

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | deferred | - | - | - | - | - | - | - | - | - |
| hola | error | - | - | - | - | - | - | - | - | - |
| ogdf | deferred | - | - | - | - | - | - | - | - | - |
| domus | error | - | - | - | - | - | - | - | - | - |
| wueortho | deferred | - | - | - | - | - | - | - | - | - |
| ogdf_libavoid | deferred | - | - | - | - | - | - | - | - | - |

*Grid not available for xlarge_state_machine*

## Recommendations

Composite score = 0.4 * port_violations + 0.3 * edge_crossings + 0.2 * bend_count + 0.1 * same_instr_cluster_dist (lower is better, averaged across all 'ok' binaries; Tier 1 candidates with at least one successful run only).

| Candidate | Composite Score |
|---|---|
| hola | 24.46 |

## Caveats

- **libavoid**: DEFERRED - adaptagrams: No module named 'adaptagrams'
- **hola**: 4/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **ogdf**: DEFERRED - ogdf_python: ogdf-python couldn't load OGDF (or one of its dependencies like COIN) in mode 'release'.
Please check the above underlying error and check that the below search paths contain OGDF headers and shared libraries in the correct release/debug configuration.
If you haven't installed OGDF globally to your system, you can use the environment variables OGDF_INSTALL_DIR or OGDF_BUILD_DIR.
The current search path is:
.:/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/lib:/usr/lib/glibc-hwcaps/x86-64-v3:/usr/lib/glibc-hwcaps/x86-64-v2:/usr/lib:/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib
The current include path is:
-I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/etc/" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/etc//cling" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/include/" -I"/usr/include/python3.14" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/../../../include/site/python3.14" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/include"

- **domus**: 5/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **wueortho**: DEFERRED - java present at /usr/bin/java but sbt missing; WueOrtho needs sbt
- **ogdf_libavoid**: DEFERRED - ogdf(ogdf_python: ogdf-python couldn't load OGDF (or one of its dependencies like COIN) in mode 'release'.
Please check the above underlying error and check that the below search paths contain OGDF headers and shared libraries in the correct release/debug configuration.
If you haven't installed OGDF globally to your system, you can use the environment variables OGDF_INSTALL_DIR or OGDF_BUILD_DIR.
The current search path is:
.:/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/lib:/usr/lib/glibc-hwcaps/x86-64-v3:/usr/lib/glibc-hwcaps/x86-64-v2:/usr/lib:/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib
The current include path is:
-I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/etc/" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/etc//cling" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/cppyy_backend/include/" -I"/usr/include/python3.14" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/lib/python3.14/site-packages/../../../include/site/python3.14" -I"/home/patacca/patacca_git/flatline/benchmarks/xray_layout/.venv-bench/include"
); libavoid(adaptagrams: No module named 'adaptagrams')
