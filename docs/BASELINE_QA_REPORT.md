> Historical imported baseline. For this new repository and C++ milestone, see
> [current implementation report](IMPLEMENTATION_REPORT.md).

# Baseline QA report

Baseline commit `a71c547`, executed 2026-10-28 before foundation implementation.
Machine-readable evidence: [baseline.json](evidence/baseline.json).

| Check | Actual result |
|---|---|
| Common Python tests | 966 passed, 2 skipped, 0 failed; 20.34 s |
| Backend line coverage | 96.90% (5152/5317 statements), real pytest-cov run |
| Desktop logic | 216 passed, 1 skipped |
| Desktop diagnostic E2E / negative | 6 / 68 passed |
| Desktop UI page objects / widgets | 142 / 25 passed, offscreen Qt |
| Desktop aggregate / production-core coverage | 90.43% / 90.84% |
| Android JVM | 113 cases, 0 failures, 0 errors, 0 skipped; Gradle tasks include cached work |
| Android build | Kotlin + instrumentation compilation, assembleDebug, lintDebug successful; 67 tasks, 66 up-to-date |
| Deterministic golden performance | p50 0.57 ms, p95 0.85 ms, 100 measured + 10 warm-up runs |
| Golden/performance focused regressions | 5 passed |
| Real ELM/vehicle tests | NOT EXECUTED; no attached hardware |
| iOS build/tests | BLOCKED; no macOS/Xcode |
| Windows EXE/Setup execution | BLOCKED; Linux host |

Counts overlap between common and Desktop selections and must not be summed
as unique test cases. Local p95 includes fixture copying and deterministic
analysis, not network/OBD time, LLM inference, startup or field performance.
No C++ coverage exists because no C++ core exists. Backend line coverage does
not prove authentication, contact delivery or production tenant isolation;
those features were absent at baseline. Android instrumentation was compiled,
not executed on a device in this run.

Commands: `python -m pytest tests --cov=backend`,
`python scripts/run_desktop_tests.py --min-core-coverage 90`, and local Gradle
`:app:compileDebugKotlin :app:compileDebugAndroidTestKotlin :app:testDebugUnitTest
:app:assembleDebug :app:lintDebug`. All work is local, without CI/CD.
