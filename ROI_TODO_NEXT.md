# ROI Next Session

Current backend status:
- ROI engine supports monthly underwriting, levered/unlevered returns, FCFF/FCFE, WACC inputs, lease-aware cash flows, stress testing, Monte Carlo simulation, correlated shocks, risk-adjusted ranking, attribution, recommendation logic, benchmark assessment, actuals-vs-underwriting variance, and benchmark comp calibration.
- Latest pushed commit: `0b6b983` (`Add benchmark comps and ROI variance analysis`).
- Before running against Postgres again, run `alembic upgrade head` in `platform-core`.

Highest-priority next work:
1. Frontend ROI analysis UX
- Show recommendation, conviction, rationale, and required assumption checks.
- Show benchmark assessment and calibrated comp ranges.
- Show actuals entry and variance dashboard in the project workspace.

2. External data ingestion
- Add feed/import path for benchmark comps instead of manual-only entry.
- Support CSV/JSON upload for comps.
- Map ingested comps by asset class and geography.

3. Benchmark intelligence
- Add geography-aware benchmark calibration, not just asset-class-level.
- Add confidence decay for stale comps.
- Add comp selection/exclusion controls and outlier handling.

4. Variance intelligence
- Add reforecast logic after actuals are recorded.
- Compare trailing actual performance to original scenario recommendation.
- Flag when a scenario should move from `invest` to `watch` or `reject`.

5. Analysis quality upgrades
- Add sector-specific model packs beyond current defaults.
- Add richer lease metrics like WALT, rollover exposure, and mark-to-market gap.
- Add QoE/accounting anomaly checks backed by uploaded financial statements.

6. Portfolio analysis
- Aggregate benchmark-adjusted ranking across projects.
- Add capital allocation and concentration-risk views.
- Add downside portfolio stress testing.

Immediate restart suggestion:
1. Build frontend support for benchmark assessment, recommendation, and variance analysis.
2. Then add comp import so calibrated benchmarks can be populated faster.
