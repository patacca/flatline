---
generated_at: "2026-04-20T19:59:02.121116+00:00"
git_sha: "65aecd8"
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
| sugiyama_libavoid | Tier 1 | 4/5 |
| ogdf_planarization | Tier 1 | 5/5 |

> See [`DOMUS_INVESTIGATION.md`](DOMUS_INVESTIGATION.md) for the DOMUS adapter/extractor fix journey and viability analysis.

## Results by Binary

### tiny_branch

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 133.0 | 0.3 | 10880.0 | 0.9 | 0.0 | 115200.0 | 2.0 | 16.0 | 5.0 | 302.5 |
| ogdf_libavoid | ok | 11.0 | 0.4 | 6176.9 | 22.8 | 0.0 | 214321.0 | 1.3 | 16.0 | 2.0 | 235.7 |
| ogdf | ok | 1.0 | 0.7 | 7008.3 | 23.4 | 101.0 | 214321.0 | 1.3 | 16.0 | 0.0 | 235.7 |
| sugiyama_libavoid | ok | 42.0 | 0.8 | 15128.1 | 76.7 | 60.0 | 589000.0 | 0.7 | 16.0 | 2.0 | 199.1 |
| hola | ok | 8.0 | 0.6 | 6761.6 | 90.5 | 0.0 | 284155.4 | 1.5 | 16.0 | 2.0 | 203.5 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

![tiny_branch grid](renders/tiny_branch__GRID.png)

### small_loop

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 631.0 | 0.3 | 32120.0 | 2.1 | 0.0 | 345600.0 | 1.5 | 34.0 | 4.0 | 344.0 |
| ogdf | ok | 12.0 | 0.7 | 18663.8 | 35.6 | 189.0 | 849375.0 | 1.5 | 34.0 | 0.0 | 268.5 |
| domus | ok | 11.0 | 1.0 | 23971.8 | 40.8 | 0.0 | 7332532.1 | 0.8 | 16.0 | 0.0 | 880.1 |
| ogdf_libavoid | ok | 33.0 | 0.3 | 18476.1 | 41.2 | 0.0 | 739171.0 | 1.8 | 34.0 | 2.0 | 166.5 |
| sugiyama_libavoid | ok | 129.0 | 0.7 | 43529.4 | 294.6 | 84.0 | 2310166.7 | 0.3 | 34.0 | 2.0 | 288.2 |
| hola | ok | 84.0 | 0.7 | 22598.9 | 1138.1 | 0.0 | 1443606.0 | 1.3 | 34.0 | 6.0 | 379.3 |

![small_loop grid](renders/small_loop__GRID.png)

### medium_switch

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 610.0 | 0.3 | 34080.0 | 2.4 | 0.0 | 403200.0 | 1.8 | 38.0 | 1.0 | 373.1 |
| ogdf | ok | 6.0 | 0.7 | 18086.1 | 39.9 | 194.0 | 876905.0 | 1.3 | 38.0 | 0.0 | 301.5 |
| ogdf_libavoid | ok | 23.0 | 0.3 | 18566.2 | 45.1 | 0.0 | 1096378.6 | 0.9 | 38.0 | 2.0 | 217.5 |
| sugiyama_libavoid | ok | 93.0 | 0.8 | 59290.7 | 155.2 | 92.0 | 4580550.0 | 0.3 | 38.0 | 5.0 | 625.5 |
| hola | ok | 36.0 | 0.7 | 20247.7 | 793.8 | 0.0 | 1267175.0 | 1.5 | 38.0 | 2.0 | 281.7 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

![medium_switch grid](renders/medium_switch__GRID.png)

### large_nested

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 12616.0 | 0.2 | 290760.0 | 28.1 | 0.0 | 1622400.0 | 1.5 | 158.0 | 9.0 | 707.1 |
| ogdf_libavoid | ok | 652.0 | 0.2 | 198815.0 | 1276.0 | 0.0 | 11281745.4 | 1.5 | 158.0 | 3.0 | 727.7 |
| ogdf | ok | 170.0 | 0.6 | 164464.8 | 2150.8 | 909.0 | 9397329.5 | 1.3 | 158.0 | 0.0 | 497.9 |
| sugiyama_libavoid | ok | 2094.0 | 0.8 | 1309540.9 | 129634.0 | 521.0 | 118882566.7 | 0.2 | 158.0 | 5.0 | 2680.0 |
| hola | ok | 714.0 | 0.6 | 167480.4 | 212340.5 | 0.0 | 8336944.0 | 1.4 | 158.0 | 7.0 | 557.4 |
| domus | timeout | - | - | - | - | - | - | - | - | - | - |

![large_nested grid](renders/large_nested__GRID.png)

### xlarge_state_machine

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 62851.0 | 0.2 | 944720.0 | 126.8 | 0.0 | 3648000.0 | 1.6 | 344.0 | 173.0 | 1098.3 |
| ogdf_libavoid | ok | 1977.0 | 0.2 | 610862.8 | 17538.7 | 0.0 | 42009303.9 | 1.2 | 344.0 | 89.0 | 965.4 |
| ogdf | ok | 727.0 | 0.7 | 670281.3 | 27782.2 | 2158.0 | 42520369.5 | 1.1 | 344.0 | 0.0 | 815.0 |
| hola | timeout | - | - | - | - | - | - | - | - | - | - |
| domus | timeout | - | - | - | - | - | - | - | - | - | - |
| sugiyama_libavoid | timeout | - | - | - | - | - | - | - | - | - | - |

![xlarge_state_machine grid](renders/xlarge_state_machine__GRID.png)

## Recommendations

Composite score = 0.4 * port_violations + 0.3 * edge_crossings + 0.2 * bend_count + 0.1 * same_instr_cluster_dist (lower is better, averaged across all 'ok' binaries; Tier 1 candidates with at least one successful run only).

| Candidate | Composite Score |
|---|---|
| ogdf_planarization | 0.00 |
| domus | 97.71 |
| hola | 123.30 |
| ogdf_libavoid | 255.21 |
| ogdf | 286.57 |
| sugiyama_libavoid | 334.12 |
| libavoid | 4714.16 |

## Caveats

- **hola**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **domus**: 4/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **sugiyama_libavoid**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
