from fastapi import FastAPI


# Developer: Ravi Kafley
# Placeholder service boundary for retail forecasting workloads.
app = FastAPI(title="Forecast Service", version="0.1.0")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Basic probe endpoint for orchestration and local checks."""
    return {"status": "ok", "service": "forecast-service"}
