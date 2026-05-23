from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Screener Scoring Service")


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="scoring")
