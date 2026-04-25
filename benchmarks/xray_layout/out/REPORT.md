---
generated_at: "2026-04-25T11:42:43.747389+00:00"
git_sha: "2702993"
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
| libavoid | Tier 1 | 5/5 |
| hola | Tier 1 | 4/5 |
| ogdf | Tier 1 | 5/5 |
| domus | Tier 1 | 1/5 |
| ogdf_libavoid | Tier 1 | 5/5 |
| sugiyama_libavoid | Tier 1 | 5/5 |
| ogdf_planarization | Tier 1 | 5/5 |

> See [`DOMUS_INVESTIGATION.md`](DOMUS_INVESTIGATION.md) for the DOMUS adapter/extractor fix journey and viability analysis.

## Results by Binary

### tiny_branch

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 168.0 | 1.0 | 10964.4 | 2.8 | 65.0 | 115200.0 | 2.0 | 18.0 | 0.0 | 302.5 |
| ogdf_planarization | ok | 1.0 | 0.7 | 9605.9 | 4.3 | 103.0 | 333045.0 | 1.3 | 16.0 | 0.0 | 186.9 |
| sugiyama_libavoid | ok | 34.0 | 1.0 | 7547.6 | 10.1 | 37.0 | 396000.0 | 0.8 | 16.0 | 0.0 | 159.8 |
| ogdf_libavoid | ok | 32.0 | 1.0 | 6130.0 | 23.5 | 25.0 | 214321.0 | 1.3 | 17.0 | 2.0 | 235.7 |
| ogdf | ok | 1.0 | 0.7 | 7008.3 | 26.0 | 101.0 | 214321.0 | 1.3 | 16.0 | 0.0 | 235.7 |
| hola | ok | 11.0 | 1.0 | 6951.6 | 90.5 | 19.0 | 284155.4 | 1.5 | 16.0 | 0.0 | 203.5 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

![tiny_branch grid](renders/tiny_branch__GRID.png)

### small_loop

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 702.0 | 1.0 | 32564.5 | 11.0 | 152.0 | 345600.0 | 1.5 | 32.0 | 7.0 | 344.0 |
| ogdf_planarization | ok | 11.0 | 0.5 | 19675.0 | 13.9 | 188.0 | 1013885.0 | 1.4 | 34.0 | 0.0 | 346.4 |
| domus | ok | 11.0 | 1.0 | 23971.8 | 35.9 | 0.0 | 7332532.1 | 0.8 | 16.0 | 0.0 | 880.1 |
| sugiyama_libavoid | ok | 57.0 | 1.0 | 23908.8 | 36.2 | 86.0 | 1306500.0 | 0.5 | 34.0 | 0.0 | 213.3 |
| ogdf | ok | 11.0 | 0.7 | 17552.5 | 39.5 | 195.0 | 778757.8 | 1.1 | 34.0 | 0.0 | 183.1 |
| ogdf_libavoid | ok | 47.0 | 1.0 | 20017.5 | 48.2 | 37.0 | 873807.8 | 0.9 | 46.0 | 4.0 | 311.1 |
| hola | ok | 65.0 | 1.0 | 23271.1 | 1099.4 | 41.0 | 1443606.0 | 1.3 | 34.0 | 0.0 | 379.3 |

![small_loop grid](renders/small_loop__GRID.png)

### medium_switch

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 640.0 | 1.0 | 34534.7 | 11.5 | 149.0 | 403200.0 | 1.8 | 42.0 | 0.0 | 373.1 |
| ogdf_planarization | ok | 6.0 | 0.6 | 17677.5 | 27.4 | 213.0 | 923693.9 | 1.4 | 38.0 | 0.0 | 273.1 |
| sugiyama_libavoid | ok | 68.0 | 1.0 | 26775.4 | 31.9 | 89.0 | 1602000.0 | 0.8 | 38.0 | 0.0 | 335.3 |
| ogdf | ok | 6.0 | 0.7 | 18086.1 | 40.0 | 194.0 | 876905.0 | 1.3 | 38.0 | 0.0 | 301.5 |
| ogdf_libavoid | ok | 45.0 | 1.0 | 19575.7 | 48.8 | 45.0 | 961185.7 | 1.7 | 46.0 | 7.0 | 263.3 |
| hola | ok | 34.0 | 1.0 | 20408.0 | 833.8 | 42.0 | 1267175.0 | 1.5 | 39.0 | 0.0 | 281.7 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

![medium_switch grid](renders/medium_switch__GRID.png)

### large_nested

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 12815.0 | 1.0 | 292765.1 | 382.5 | 791.0 | 1622400.0 | 1.5 | 167.0 | 0.0 | 707.1 |
| ogdf_libavoid | ok | 509.0 | 1.0 | 138328.6 | 1702.9 | 246.0 | 9673534.0 | 1.6 | 195.0 | 17.0 | 462.0 |
| ogdf_planarization | ok | 190.0 | 0.6 | 189700.3 | 1839.0 | 948.0 | 11615166.7 | 1.0 | 158.0 | 0.0 | 492.8 |
| ogdf | ok | 202.0 | 0.6 | 170241.6 | 2837.3 | 911.0 | 10873362.3 | 1.1 | 158.0 | 0.0 | 375.4 |
| sugiyama_libavoid | ok | 1214.0 | 1.0 | 433333.5 | 3946.8 | 405.0 | 33408000.0 | 1.0 | 158.0 | 0.0 | 1118.9 |
| hola | ok | 577.0 | 1.0 | 175381.3 | 212325.8 | 293.0 | 8336944.0 | 1.4 | 159.0 | 0.0 | 557.4 |
| domus | timeout | - | - | - | - | - | - | - | - | - | - |

![large_nested grid](renders/large_nested__GRID.png)

### xlarge_state_machine

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 61305.0 | 1.0 | 949023.8 | 3484.2 | 1846.0 | 3648000.0 | 1.6 | 384.0 | 43.0 | 1098.3 |
| ogdf | ok | 887.0 | 0.6 | 829669.0 | 11914.4 | 2213.0 | 49949636.2 | 1.0 | 344.0 | 0.0 | 922.6 |
| ogdf_planarization | ok | 895.0 | 0.5 | 802061.5 | 17401.2 | 2202.0 | 49665414.7 | 1.3 | 344.0 | 0.0 | 875.2 |
| ogdf_libavoid | ok | 1730.0 | 1.0 | 686529.0 | 32964.4 | 534.0 | 47312340.7 | 1.0 | 451.0 | 342.0 | 1042.5 |
| sugiyama_libavoid | ok | 6705.0 | 1.0 | 2376351.1 | 61128.3 | 986.0 | 183727500.0 | 1.5 | 344.0 | 0.0 | 2928.0 |
| hola | timeout | - | - | - | - | - | - | - | - | - | - |
| domus | timeout | - | - | - | - | - | - | - | - | - | - |

![xlarge_state_machine grid](renders/xlarge_state_machine__GRID.png)

## Recommendations

Composite score = 0.4 * port_violations + 0.3 * edge_crossings + 0.2 * bend_count + 0.1 * same_instr_cluster_dist (lower is better, averaged across all 'ok' binaries; Tier 1 candidates with at least one successful run only).

| Candidate | Composite Score |
|---|---|
| domus | 97.71 |
| hola | 131.62 |
| ogdf_libavoid | 283.95 |
| ogdf | 298.55 |
| ogdf_planarization | 303.03 |
| sugiyama_libavoid | 691.11 |
| libavoid | 4765.86 |

## Caveats

- **hola**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **domus**: 4/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
