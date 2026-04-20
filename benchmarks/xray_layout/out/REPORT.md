---
generated_at: "2026-04-20T17:08:02.964880+00:00"
git_sha: "7f6eb5c"
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
| ogdf | Tier 1 | 4/5 |
| domus | Tier 1 | 1/5 |
| ogdf_libavoid | Tier 1 | 4/5 |
| sugiyama_libavoid | Tier 1 | 4/5 |
| ogdf_planarization | Tier 1 | 4/5 |

> See [`DOMUS_INVESTIGATION.md`](DOMUS_INVESTIGATION.md) for the DOMUS adapter/extractor fix journey and viability analysis.

## Results by Binary

### tiny_branch

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 133.0 | 0.3 | 10880.0 | 0.8 | 0.0 | 115200.0 | 2.0 | 16.0 | 5.0 | 302.5 |
| ogdf_libavoid | ok | 7.0 | 0.4 | 6100.6 | 6.9 | 0.0 | 262416.7 | 0.8 | 16.0 | 2.0 | 140.7 |
| ogdf | ok | 1.0 | 0.7 | 7008.3 | 22.4 | 101.0 | 214321.0 | 1.3 | 16.0 | 0.0 | 235.7 |
| sugiyama_libavoid | ok | 42.0 | 0.8 | 15128.1 | 72.8 | 60.0 | 589000.0 | 0.7 | 16.0 | 2.0 | 199.1 |
| hola | ok | 8.0 | 0.6 | 6761.6 | 100.4 | 0.0 | 284155.4 | 1.5 | 16.0 | 2.0 | 203.5 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

*Grid not available for tiny_branch*

### small_loop

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 631.0 | 0.3 | 32120.0 | 2.1 | 0.0 | 345600.0 | 1.5 | 34.0 | 4.0 | 344.0 |
| ogdf_libavoid | ok | 37.0 | 0.3 | 15182.5 | 16.5 | 0.0 | 840350.0 | 0.9 | 34.0 | 2.0 | 185.2 |
| domus | ok | 11.0 | 1.0 | 23971.8 | 38.1 | 0.0 | 7332532.1 | 0.8 | 16.0 | 0.0 | 880.1 |
| ogdf | ok | 11.0 | 0.7 | 17286.2 | 38.6 | 194.0 | 907603.1 | 1.3 | 34.0 | 0.0 | 185.1 |
| sugiyama_libavoid | ok | 128.0 | 0.7 | 42676.1 | 256.3 | 82.0 | 1972516.7 | 0.3 | 34.0 | 2.0 | 258.8 |
| hola | ok | 84.0 | 0.7 | 22598.9 | 1352.5 | 0.0 | 1443606.0 | 1.3 | 34.0 | 6.0 | 379.3 |

*Grid not available for small_loop*

### medium_switch

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 610.0 | 0.3 | 34080.0 | 2.5 | 0.0 | 403200.0 | 1.8 | 38.0 | 1.0 | 373.1 |
| ogdf_libavoid | ok | 21.0 | 0.4 | 16139.6 | 19.2 | 0.0 | 951296.9 | 1.1 | 38.0 | 1.0 | 186.3 |
| ogdf | ok | 6.0 | 0.7 | 18086.1 | 43.6 | 194.0 | 876905.0 | 1.3 | 38.0 | 0.0 | 301.5 |
| sugiyama_libavoid | ok | 53.0 | 0.7 | 44132.3 | 216.6 | 62.0 | 3015900.0 | 0.4 | 38.0 | 2.0 | 510.6 |
| hola | ok | 35.0 | 0.7 | 20247.8 | 926.1 | 0.0 | 1267175.0 | 1.5 | 38.0 | 2.0 | 281.7 |
| domus | error | - | - | - | - | - | - | - | - | - | - |

*Grid not available for medium_switch*

### large_nested

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ogdf_planarization | ok | 0.0 | 0.0 | 0.0 | 0.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| libavoid | ok | 12616.0 | 0.2 | 290760.0 | 31.2 | 0.0 | 1622400.0 | 1.5 | 158.0 | 9.0 | 707.1 |
| ogdf | ok | 183.0 | 0.6 | 169053.1 | 1079.0 | 900.0 | 10074634.3 | 1.3 | 158.0 | 0.0 | 412.5 |
| ogdf_libavoid | ok | 456.0 | 0.2 | 165365.8 | 1681.5 | 0.0 | 10494505.8 | 1.2 | 158.0 | 5.0 | 439.8 |
| sugiyama_libavoid | ok | 1585.0 | 0.8 | 1296761.1 | 70556.0 | 458.0 | 129199769.3 | 0.3 | 158.0 | 33.0 | 2741.3 |
| hola | ok | 714.0 | 0.6 | 167480.4 | 244160.2 | 0.0 | 8336944.0 | 1.4 | 158.0 | 7.0 | 557.4 |
| domus | timeout | - | - | - | - | - | - | - | - | - | - |

*Grid not available for large_nested*

### xlarge_state_machine

| Candidate | Status | edge_crossings | orthogonal_segment_ratio | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 62851.0 | 0.2 | 944720.0 | 138.9 | 0.0 | 3648000.0 | 1.6 | 344.0 | 173.0 | 1098.3 |
| hola | error | - | - | - | - | - | - | - | - | - | - |
| ogdf | error | - | - | - | - | - | - | - | - | - | - |
| domus | error | - | - | - | - | - | - | - | - | - | - |
| ogdf_libavoid | error | - | - | - | - | - | - | - | - | - | - |
| sugiyama_libavoid | error | - | - | - | - | - | - | - | - | - | - |
| ogdf_planarization | error | - | - | - | - | - | - | - | - | - | - |

*Grid not available for xlarge_state_machine*

## Recommendations

Composite score = 0.4 * port_violations + 0.3 * edge_crossings + 0.2 * bend_count + 0.1 * same_instr_cluster_dist (lower is better, averaged across all 'ok' binaries; Tier 1 candidates with at least one successful run only).

| Candidate | Composite Score |
|---|---|
| ogdf_planarization | 0.00 |
| ogdf_libavoid | 87.48 |
| domus | 97.71 |
| hola | 123.22 |
| ogdf | 137.49 |
| sugiyama_libavoid | 286.05 |
| libavoid | 4714.16 |

## Caveats

- **hola**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **ogdf**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **domus**: 4/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **ogdf_libavoid**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **sugiyama_libavoid**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **ogdf_planarization**: 1/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
