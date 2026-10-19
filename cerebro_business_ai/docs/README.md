# CEREBRO documentation index

Start with the [root README](../README.md).

## Current handover documentation

- [FRIEND_HANDOVER.md](FRIEND_HANDOVER.md): exactly which folder to launch, sharing/privacy checklist, setup, recovery, sample workflows and troubleshooting.
- [TECHNICAL_HANDBOOK.md](TECHNICAL_HANDBOOK.md): current architecture, model inputs/outputs, API examples, forecasting limitations, artifact locations, environment configuration, development commands, testing and maintenance.
- [Portable README](../release/Cerebro_Windows_x64/README_FIRST.md): instructions inside the runnable distribution.
- [Portable validation record](../release/Cerebro_Windows_x64/VALIDATION.md): actual executed checks and hardware observations.
- [Model/source notices](../release/Cerebro_Windows_x64/MODEL_SOURCES.md): upstream sources and licensing caveats.

## Useful implementation history

- [Scenario and currency upgrade](../SCENARIO_CURRENCY_UPGRADE.md)
- [Forecast reliability work](../FORECAST_RELIABILITY.md)
- [Job/forecast usability report](../JOB_FORECAST_USABILITY_REPORT.md)
- [Resource management](../RESOURCE_MANAGEMENT.md)
- [Phase 4](../PHASE4.md): historical fraud and M5 experiments
- [Original Phase 1 README](archive/README_PHASE1_ORIGINAL.md)
- [Original Phase 1 build/demo notes](archive/BUILD_DEMO_PHASE1_ORIGINAL.md)

The project progressed through several architectures. Older root reports, `api.md`, the Spring Boot prototype and phase documents are retained as history. In particular, old statements about no RAG, synthetic-only datasets, a mandatory Java/PostgreSQL runtime, or deterministic fallback-as-generation do **not** describe the current portable FastAPI application. Some legacy routes still exist and have different behavior; use the current gateway routes documented in the handbook.

Do not run old training, dataset-generation or Docker commands merely to launch the current application. Training and raw dataset acquisition are separate operations, subject to resource limits, licensing and explicit authorization.
