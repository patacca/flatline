# INSTALL_wueortho

## Status
DEFERRED

## Repo URL
- Active: https://github.com/WueGD/wueortho (Scala, MIT)
- Archived predecessor: https://github.com/hegetim/wueortho

## Commands Tried
```bash
gh search repos WueOrtho
gh api repos/WueGD/wueortho
```

The repo is alive (last update 2026-04, language Scala, not archived)
but has no PyPI release, no Python bindings, and no CLI distribution.

## Result
No integration path is currently available from Python directly. WueOrtho
is built as a Scala / sbt project; running it requires the JVM and the
`sbt` build tool. Two integration options for Wave 2:

1. **JVM subprocess.** Build a fat-jar (`sbt assembly`) and invoke it
   from the adapter, exchanging graph descriptions and layout results
   via files (text or JSON). This mirrors the DOMUS adapter pattern.
2. **HTTP service.** Stand WueOrtho up as a small REST service and have
   the adapter speak HTTP to it. Heavier infrastructure, but isolates
   JVM startup cost.

## System Dependencies
- JVM 11+ (OpenJDK is fine)
- sbt 1.x
- ~1 GB free disk for sbt's first build (downloads ivy/coursier deps)

## Recommendation
Defer. Lowest-risk Wave 2 path: provision sbt + JDK on the bench host,
build the fat-jar once, then implement the adapter as a subprocess
wrapper using a JSON exchange format. Budget at least one full day for
the first cut, including learning the upstream graph file schema.
