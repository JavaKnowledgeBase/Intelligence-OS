# Torilaure Intelligence OS User Manual

This guide is written for non-technical users and provides step-by-step instructions to use the Torilaure platform for project investment analysis, ROI scenario modeling, and recommendation reporting.

## 1. What this platform does

Torilaure Intelligence OS helps investment teams do these key tasks:

- Create and manage real estate / asset project workspaces
- Upload supporting documents (leases, financials, due diligence) in one place
- Model multiple ROI scenarios (base, upside, downside, custom)
- Run full ROI analysis (IRR, NPV, equity multiple, DSCR, stress tests)
- Generate data-driven recommendations (invest/watch/reject)
- Persist recommendations for audit and collaboration
- Download recommendations as a PDF report

## 2. Quick access

Open the app in a browser (default `http://localhost:5174` for local deployment). The recommended authentication path is:

1. Log in with your email/password credentials.
2. If you do not have an account, click `Create account` and follow the prompts.
3. New user accounts can request admin access if needed.

## 3. Main screens

### 3.1 Dashboard

Use the dashboard to:

- See active deals and project status at a glance
- Monitor key market signals and trends
- Review portfolio-level metrics and risk indicators

### 3.2 Projects

Each project has a workspace with sections for:

- Project summary, team members, and status
- Listings & opportunity details (deal score, IRR, location)
- Uploaded documents (PDFs, spreadsheets)
- ROI scenario engine (calculator, snapshots, scenario list)
- Notes and audit activity

### 3.3 ROI scenario engine

From the Project workspace:

1. Enter ROI assumptions in the form (purchase price, revenue, expenses, capex, financing, hold period, etc.)
2. Choose scenario type (base/upside/downside/custom)
3. Click `Preview ROI` to compute a temporary output without saving
4. Click `Sensitivity` to view risk impact by changing exit cap rate and revenue growth
5. Click `Save scenario` to store the scenario in the project
6. Saved scenarios appear in the list and summary cards update automatically

## 4. Analysis results explained

After preview or calculation, outputs include:

- Projected IRR and NPV
- Equity multiple and cash-on-cash
- Levered and unlevered returns
- DSCR metrics (average/min) for debt capacity
- Payback period
- Benchmark comparisons in the insight panel

## 5. Recommendation workflow

Once you have a saved ROI scenario, follow these steps:

1. Pick the scenario from the recommendation dropdown.
2. Click `Capture recommendation` to run the internal recommendation engine.
3. The platform stores a recommendation record with:
   - decision (`invest/watch/reject`)
   - conviction level (`low/medium/high`)
   - numeric score
   - rationale statements
   - required assumption checks
   - action items to follow up
4. Use the recommendations list to review prior decisions and context.
5. Click `Download PDF` to save a shareable report for stakeholders.

## 6. Document upload and evidence management

- Use the `Upload project document` button to attach files.
- Files are stored with metadata and are accessible from the workspace.
- Preview text is available for processed documents.
- Download original files as needed.

## 7. Team collaboration

- Add project members by email (admin/analyst roles can manage).
- Remove access for team members as needed.
- Notes and activity feed allow progress tracking and team coordination.

## 8. Best practices

- Always start with a base case and then build upside/downside scenarios.
- Validate key assumptions (growth rates, exit cap, leverage, cost inflation) in writing.
- Keep your project documents updated so valuation assumptions have supporting evidence.
- Review audit recommendation history before final investment decisions.

## 9. Troubleshooting

- If the app does not load, ensure backend is running (e.g. `uvicorn app.main:app --reload --port 8000`).
- Confirm environment variables in `.env` match your local PostgreSQL/Redis settings.
- If a fee or assumption appears wrong, update the scenario and re-run `Preview ROI`.
- Contact your platform administrator if you cannot access project data or get HTTP 403/401 errors.

## 10. Support and feedback

The platform is evolving, and your feedback is vital.

- Document feature requests in the project backlog.
- Report critical issues with reproducible steps.
- Suggest new KPI panels and benchmarking metric types for strengthening decision analytics.

---

*This user manual is designed to be clear and actionable for non-technical analysts and managers. Keep it nearby as your team builds workflow discipline in investment diligence.*