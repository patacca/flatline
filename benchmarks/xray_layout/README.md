# xray Layout Library Benchmark

> **WARNING: DO NOT MERGE TO MAIN** — This is a throwaway research branch.
> All findings live in `out/REPORT.md` and inform future work, not this codebase.

## Purpose

Data-driven evaluation of orthogonal layout libraries as candidates to replace
xray's custom placement+routing algorithm. Candidates: libavoid, HOLA, OGDF,
DOMUS, WueOrtho, OGDF+libavoid combo.

## Quickstart

See install instructions below (to be filled in by Task 9).

## Branch Policy

This branch (`bench/xray-layout-comparison`) is a throwaway research artifact.
It MUST NOT be merged to main. The benchmark harness lives entirely under
`benchmarks/xray_layout/` with zero diff against main outside this directory.
