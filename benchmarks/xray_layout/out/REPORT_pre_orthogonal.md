---
generated_at: "2026-04-20T10:52:40.376951+00:00"
git_sha: "2fea995"
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
| hola | Tier 1 | 3/5 |
| ogdf | Tier 1 | 5/5 |
| domus | Tier 1 | 1/5 |
| ogdf_libavoid | Tier 1 | 5/5 |

> See [`DOMUS_INVESTIGATION.md`](DOMUS_INVESTIGATION.md) for the DOMUS adapter/extractor fix journey and viability analysis.

## Results by Binary

### tiny_branch

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 105.0 | 10880.0 | 0.8 | 0.0 | 115200.0 | 2.0 | 16.0 | 7.0 | 302.5 |
| ogdf_libavoid | ok | 17.0 | 6981.7 | 11.0 | 0.0 | 236198.1 | 1.1 | 16.0 | 2.0 | 306.4 |
| ogdf | ok | 1.0 | 7008.3 | 20.3 | 101.0 | 214321.0 | 1.3 | 16.0 | 0.0 | 235.7 |
| hola | ok | 8.0 | 6761.6 | 93.9 | 0.0 | 284155.4 | 1.5 | 16.0 | 2.0 | 203.5 |
| domus | error | - | - | - | - | - | - | - | - | - |

*Grid not available for tiny_branch*

### small_loop

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 553.0 | 32120.0 | 2.0 | 0.0 | 345600.0 | 1.5 | 34.0 | 10.0 | 344.0 |
| ogdf_libavoid | ok | 23.0 | 14223.8 | 23.6 | 0.0 | 729925.0 | 1.3 | 34.0 | 2.0 | 159.3 |
| domus | ok | 11.0 | 23971.8 | 35.7 | 0.0 | 7332532.1 | 0.8 | 16.0 | 0.0 | 880.1 |
| ogdf | ok | 11.0 | 23557.5 | 36.0 | 193.0 | 1167958.7 | 1.8 | 34.0 | 0.0 | 378.0 |
| hola | ok | 84.0 | 22598.9 | 1170.5 | 0.0 | 1443606.0 | 1.3 | 34.0 | 6.0 | 379.3 |

*Grid not available for small_loop*

### medium_switch

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 537.0 | 34080.0 | 2.1 | 0.0 | 403200.0 | 1.8 | 38.0 | 12.0 | 373.1 |
| ogdf_libavoid | ok | 12.0 | 16139.6 | 26.4 | 0.0 | 951296.9 | 1.1 | 38.0 | 2.0 | 186.3 |
| ogdf | ok | 6.0 | 17398.8 | 38.8 | 192.0 | 919600.0 | 1.2 | 38.0 | 0.0 | 275.3 |
| hola | ok | 35.0 | 20247.8 | 821.3 | 0.0 | 1267175.0 | 1.5 | 38.0 | 2.0 | 281.7 |
| domus | error | - | - | - | - | - | - | - | - | - |

*Grid not available for medium_switch*

### large_nested

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 12146.0 | 290760.0 | 68.0 | 0.0 | 1622400.0 | 1.5 | 158.0 | 113.0 | 707.1 |
| ogdf | ok | 208.0 | 196958.6 | 1688.8 | 915.0 | 12173876.5 | 1.2 | 158.0 | 0.0 | 478.0 |
| ogdf_libavoid | ok | 399.0 | 145820.1 | 1919.4 | 0.0 | 8100622.9 | 1.3 | 158.0 | 5.0 | 444.3 |
| hola | timeout | - | - | - | - | - | - | - | - | - |
| domus | timeout | - | - | - | - | - | - | - | - | - |

*Grid not available for large_nested*

### xlarge_state_machine

| Candidate | Status | edge_crossings | total_edge_length | runtime_ms | bend_count | bbox_area | bbox_aspect | port_violations | edge_overlaps | same_instr_cluster_dist |
|---|---|---|---|---|---|---|---|---|---|---|
| libavoid | ok | 61788.0 | 944720.0 | 120.6 | 0.0 | 3648000.0 | 1.6 | 344.0 | 490.0 | 1098.3 |
| ogdf_libavoid | ok | 1876.0 | 645831.9 | 12916.1 | 0.0 | 43325460.3 | 1.2 | 344.0 | 90.0 | 947.0 |
| ogdf | ok | 749.0 | 694389.6 | 14111.6 | 2196.0 | 47680278.7 | 1.2 | 344.0 | 0.0 | 892.6 |
| hola | timeout | - | - | - | - | - | - | - | - | - |
| domus | timeout | - | - | - | - | - | - | - | - | - |

*Grid not available for xlarge_state_machine*

## Recommendations

Composite score = 0.4 * port_violations + 0.3 * edge_crossings + 0.2 * bend_count + 0.1 * same_instr_cluster_dist (lower is better, averaged across all 'ok' binaries; Tier 1 candidates with at least one successful run only).

| Candidate | Composite Score |
|---|---|
| hola | 53.25 |
| domus | 97.71 |
| ogdf_libavoid | 227.69 |
| ogdf | 294.77 |
| libavoid | 4611.44 |

## Caveats

- **hola**: 2/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
- **domus**: 4/5 binaries failed (error/crashed/timeout); see individual run JSONs in out/runs/.
