from fastapi import FastAPI


# Developer: Ravi Kafley
# Placeholder service boundary for valuation and scenario analysis workloads.
app = FastAPI(title="Valuation Service", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Basic probe endpoint for orchestration and local checks."""
    return {"status": "ok", "service": "valuation-service"}
