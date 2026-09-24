from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.middleware import SecurityHeadersMiddleware, RateLimitMiddleware
from app.netgate import get_audit_summary
from app.services.license import get_license_status
from app.routers import (
    samples, variants, qc, cohorts, pipelines,
    reports, audit, annotate, acmg, export, orgs, compliance, license,
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
    acmg.router, export.router, compliance.router, license.router,
]:
    app.include_router(r)

if settings.is_cloud:
    app.include_router(orgs.router)

if settings.is_local:
    from app.routers import local_auth
    app.include_router(local_auth.router)


@app.get("/health")
def health():
    lic = get_license_status()
    return {
        "status": "ok",
        "mode": settings.MODE,
        "offline": settings.is_offline,
        "engine_version": settings.ACMG_ENGINE_VERSION,
        "license_tier": lic["tier"],
        "license_valid": lic["valid"],
        "network_policy": lic["network_policy"],
    }


@app.get("/health/offline")
def health_offline():
    return get_audit_summary()


@app.get("/support")
def support_info():
    return {
        "email": settings.SUPPORT_EMAIL,
        "url": settings.SUPPORT_URL,
    }


@app.on_event("startup")
async def startup_banner():
    lic = get_license_status()
    print("=" * 70)
    print(f"  GenomicsOps backend started")
    print(f"  Mode:           {settings.MODE}")
    print(f"  ACMG engine:    {settings.ACMG_ENGINE_VERSION}")
    print(f"  License tier:   {lic['tier']}  ({'valid' if lic['valid'] else 'invalid'})")
    print(f"  Network policy: {lic['network_policy']}")
    if lic["days_remaining"] is not None:
        print(f"  License expires in {lic['days_remaining']} days")
    if lic["grace_period_active"]:
        print(f"  ⚠ GRACE PERIOD ACTIVE — license expired, working within grace window")
    print("=" * 70)
