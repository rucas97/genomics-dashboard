from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.routers import (
    samples, variants, qc, cohorts, pipelines,
    reports, audit, annotate, acmg, export, orgs, compliance,
)

app = FastAPI(title="Genomics Dashboard API", version="0.1.0")

# Order matters: CORS first, then security, then rate limit
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit=120, window=60)

for r in [
    samples.router, variants.router, qc.router, cohorts.router,
    pipelines.router, reports.router, audit.router, annotate.router,
    acmg.router, export.router, orgs.router, compliance.router,
]:
    app.include_router(r)

@app.get("/health")
def health():
    return {"status": "ok"}
