---
generated_at: "2026-04-20T20:37:17.317471+00:00"
git_sha: "de4a1b3"
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
| libavoid | ok | 170.0 | 1.0 | 10916.4 | 3.7 | 65.0 | 115200.0 | 2.0 | 18.0 | 0.0 | 302.5 |
| ogdf | ok | 1.0 | 0.7 | 7008.3 | 18.3 | 101.0 | 214321.0 | 1.3 | 16.0 | 0.0 | 235.7 |
| ogdf_libavoid | ok | 34.0 | 1.0 | 6128.9 | 24.4 | 25.0 | 214321.0 | 1.3 | 15.0 | 0.0 | 235.7 |
| sugiyama_libavoid | ok | 42.0 | 0.8 | 15128.1 | 74.3 | 60.0 | 589000.0 | 0.7 | 16.0 | 2.0 | 199.1 |
| hola | ok | 8.0 | 0.6 | 6761.6 | 94.2 | 0.0 | 284155.4 | 1.5 | 16.0 | 2.0 | 203.5 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

*Grid not available for tiny_branch*

### small_loop

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 609.0 | 1.0 | 32412.4 | 20.7 | 152.0 | 345600.0 | 1.5 | 33.0 | 132.0 | 344.0 |
| ogdf | ok | 9.0 | 0.6 | 18332.7 | 36.7 | 188.0 | 866730.7 | 1.4 | 34.0 | 0.0 | 320.0 |
| domus | ok | 11.0 | 1.0 | 23971.8 | 43.8 | 0.0 | 7332532.1 | 0.8 | 16.0 | 0.0 | 880.1 |
| ogdf_libavoid | ok | 33.0 | 1.0 | 15896.0 | 49.4 | 42.0 | 772968.8 | 1.5 | 45.0 | 5.0 | 169.3 |
| sugiyama_libavoid | ok | 129.0 | 0.7 | 43529.4 | 317.9 | 84.0 | 2310166.7 | 0.3 | 34.0 | 2.0 | 288.2 |
| hola | ok | 84.0 | 0.7 | 22598.9 | 1160.4 | 0.0 | 1443606.0 | 1.3 | 34.0 | 6.0 | 379.3 |

*Grid not available for small_loop*

### medium_switch

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 636.0 | 1.0 | 34369.0 | 19.1 | 149.0 | 403200.0 | 1.8 | 42.0 | 0.0 | 373.1 |
| ogdf | ok | 6.0 | 0.6 | 16859.1 | 41.0 | 192.0 | 981601.0 | 1.2 | 38.0 | 0.0 | 218.8 |
| ogdf_libavoid | ok | 33.0 | 1.0 | 19237.6 | 47.4 | 43.0 | 909237.8 | 1.7 | 46.0 | 14.0 | 244.7 |
| sugiyama_libavoid | ok | 93.0 | 0.8 | 59290.7 | 155.1 | 92.0 | 4580550.0 | 0.3 | 38.0 | 5.0 | 625.5 |
| hola | ok | 36.0 | 0.7 | 20247.7 | 844.8 | 0.0 | 1267175.0 | 1.5 | 38.0 | 2.0 | 281.7 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

*Grid not available for medium_switch*

### large_nested

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 12844.0 | 1.0 | 292098.3 | 1173.5 | 791.0 | 1622400.0 | 1.5 | 167.0 | 0.0 | 707.1 |
| ogdf_libavoid | ok | 565.0 | 1.0 | 233342.0 | 2545.9 | 216.0 | 12284145.3 | 1.3 | 211.0 | 10.0 | 798.1 |
| ogdf | ok | 219.0 | 0.7 | 198913.1 | 3666.1 | 922.0 | 9936305.6 | 1.2 | 158.0 | 0.0 | 526.1 |
| sugiyama_libavoid | ok | 2094.0 | 0.8 | 1309540.9 | 130012.6 | 521.0 | 118882566.7 | 0.2 | 158.0 | 5.0 | 2680.0 |
| hola | ok | 714.0 | 0.6 | 167479.7 | 236674.3 | 0.0 | 8336944.0 | 1.4 | 158.0 | 7.0 | 557.4 |
| domus | timeout | - | - | - | - | - | - | - | - | - | - |

*Grid not available for large_nested*

### xlarge_state_machine

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 1.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| ogdf | ok | 800.0 | 0.7 | 700576.0 | 14440.7 | 2176.0 | 44612395.4 | 1.7 | 344.0 | 0.0 | 729.0 |
| libavoid | ok | 61461.0 | 1.0 | 947765.2 | 16118.7 | 1846.0 | 3648000.0 | 1.6 | 371.0 | 0.0 | 1098.3 |
| ogdf_libavoid | ok | 1702.0 | 1.0 | 618442.7 | 31637.6 | 560.0 | 38115505.1 | 1.3 | 417.0 | 0.0 | 841.8 |
| hola | timeout | - | - | - | - | - | - | - | - | - | - |
| domus | timeout | - | - | - | - | - | - | - | - | - | - |
| sugiyama_libavoid | timeout | - | - | - | - | - | - | - | - | - | - |

*Grid not available for xlarge_state_machine*

## Recommendations

Composite score = 0.4 * port_violations + 0.3 * edge_crossings + 0.2 * bend_count + 0.1 * same_instr_cluster_dist (lower is better, averaged across all 'ok' binaries; Tier 1 candidates with at least one successful run only).

| Candidate | Composite Score |
|---|---|
| ogdf_planarization | 0.00 |
| domus | 97.71 |
| hola | 123.30 |
| ogdf_libavoid | 281.97 |
| ogdf | 293.05 |
| sugiyama_libavoid | 334.12 |
| libavoid | 4770.30 |

## Caveats

- **hola**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **domus**: 4/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **sugiyama_libavoid**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
