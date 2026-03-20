# ROI Next Session

Current backend status:
- ROI engine supports monthly underwriting, levered/unlevered returns, FCFF/FCFE, WACC inputs, lease-aware cash flows, stress testing, Monte Carlo simulation, correlated shocks, risk-adjusted ranking, attribution, recommendation logic, benchmark assessment, actuals-vs-underwriting variance, benchmark comp calibration, recommendation drift, portfolio stress views, and scenario benchmark context.
- Frontend now includes ROI recommendation, benchmark assessment, actuals entry, variance analysis, recommendation drift, benchmark comp management, portfolio drilldowns, dashboard saved views, and backend-backed shared/personal portfolio view persistence.
- Latest local schema additions include:
  - `20260320_000017_benchmark_comp_inclusion.py`
  - `20260320_000018_benchmark_comp_override_mode.py`
  - `20260320_000019_portfolio_saved_views.py`
- Before running against Postgres or Docker again, run `alembic upgrade head` in `platform-core` or restart the stack so migrations apply.

Highest-priority next work:
1. Saved view depth
- Expand saved views from simple presets into richer criteria payloads.
- Support combinations like `retail + high fragility + ranking section`.
- Add validation so unsupported criteria do not silently degrade.

2. Saved view collaboration
- Add edit history / last-updated metadata for shared views.
- Allow admins or creators to manage team-shared portfolio lenses cleanly.
- Consider view ownership transfer or soft-delete/archive instead of hard delete only.

3. Portfolio filtering depth
- Add richer filters for project type, recommendation, fragility, and scenario type together.
- Let the dashboard show active filter chips beyond the current preset name.
- Support filtered counts instead of only overall portfolio totals.

4. Recommendation workflow depth
- Link recommendation history into dashboard-level ranking and stress views.
- Add direct scenario deep links from more recommendation surfaces.
- Consider recommendation status aging or "stale recommendation" indicators after actuals drift.

5. Analysis quality upgrades
- Add sector-specific model packs beyond current defaults.
- Add richer lease metrics like WALT, rollover exposure, and mark-to-market gap.
- Add QoE/accounting anomaly checks backed by uploaded financial statements.

6. Operational polish
- Restart Docker/backend so new migrations are applied.
- Push current branch to GitHub after final sanity check.
- Consider cleaning up workspace pytest cache permission noise if it becomes distracting.

Immediate restart suggestion:
1. Apply latest Alembic migrations and restart local Docker/backend.
2. Verify shared saved views in a real logged-in browser session.
3. Then build richer saved-view criteria payloads and filtered dashboard totals.
