from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.netgate import get_audit_summary
from app.routers import (
    samples, variants, qc, cohorts, pipelines,
    reports, audit, annotate, acmg, export, orgs, compliance,
)

app = FastAPI(title="Genomics Dashboard API", version="0.1.0")

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
    acmg.router, export.router, compliance.router,
]:
    app.include_router(r)

if settings.is_cloud:
    app.include_router(orgs.router)

if settings.is_local:
    from app.routers import local_auth
    app.include_router(local_auth.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": settings.MODE,
        "offline": settings.is_offline,
        "engine_version": settings.ACMG_ENGINE_VERSION,
    }


@app.get("/health/offline")
def health_offline():
    """Return offline enforcement status and recent blocked calls."""
    return get_audit_summary()


@app.on_event("startup")
async def startup_banner():
    print("=" * 60)
    print(f"  GenomicsOps backend started")
    print(f"  Mode:          {settings.MODE}")
    print(f"  Offline:       {settings.is_offline}")
    print(f"  ACMG engine:   {settings.ACMG_ENGINE_VERSION}")
    if settings.is_offline:
        print(f"  Network:       BLOCKED (all outbound calls raise OfflineModeError)")
    else:
        print(f"  Network:       enabled")
    print("=" * 60)
